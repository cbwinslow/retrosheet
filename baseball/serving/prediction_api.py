"""REST API for prediction serving.

Provides HTTP endpoints for:
- Health checks
- Model information
- Predictions (next-run, PA outcome)
- Batch predictions
- Cache management

Author: Agent cbwinslow/retrosheet
Date: 2026-04-26
"""

import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

from .model_server import ModelServer


logger = logging.getLogger(__name__)


class PredictionAPI:
    """REST API for model predictions.

    Endpoints:
    - GET /health - Health check
    - GET /models - List loaded models
    - GET /models/<name> - Model info
    - POST /predict/<model> - Single prediction
    - POST /predict/<model>/batch - Batch prediction
    - GET /cache/stats - Cache statistics
    - POST /cache/clear - Clear cache

    Example:
        >>> api = PredictionAPI(model_server=server)
        >>> app = api.create_app()
        >>> app.run(host='0.0.0.0', port=5000)
    """

    def __init__(
        self,
        model_server: ModelServer | None = None,
        db_connection=None,
        model_dir: str = 'models',
        enable_cache: bool = True,
    ) -> None:
        """Initialize prediction API.

        Args:
            model_server: Pre-configured model server (or None to create)
            db_connection: Database connection
            model_dir: Model directory
            enable_cache: Enable prediction caching
        """
        if model_server:
            self.server = model_server
        else:
            self.server = ModelServer(
                db_connection=db_connection,
                model_dir=model_dir,
                enable_cache=enable_cache,
            )

    def create_app(self) -> Flask:
        """Create Flask application with routes.

        Returns:
            Configured Flask app
        """
        app = Flask(__name__)
        CORS(app)  # Enable CORS for all domains

        # Health check
        @app.route('/health', methods=['GET'])
        def health():
            """Health check endpoint."""
            health_status = self.server.health_check()
            status_code = 200 if health_status['status'] == 'healthy' else 503
            return jsonify(health_status), status_code

        # List models
        @app.route('/models', methods=['GET'])
        def list_models():
            """List loaded models."""
            models = []
            for name in self.server.get_loaded_models():
                info = self.server.get_model_info(name)
                if info:
                    models.append(info)

            return jsonify(
                {
                    'models': models,
                    'count': len(models),
                },
            )

        # Model info
        @app.route('/models/<model_name>', methods=['GET'])
        def model_info(model_name: str):
            """Get model information."""
            info = self.server.get_model_info(model_name)
            if info:
                return jsonify(info)
            return jsonify({'error': 'Model not found'}), 404

        # Load model
        @app.route('/models/<model_name>/load', methods=['POST'])
        def load_model(model_name: str):
            """Load a model."""
            data = request.get_json() or {}
            version = data.get('version', 'latest')

            success = self.server.load_model(model_name, version)

            if success:
                return jsonify(
                    {
                        'success': True,
                        'model': model_name,
                        'version': version,
                    },
                )
            return jsonify(
                {
                    'success': False,
                    'error': f'Failed to load {model_name}',
                },
            ), 500

        # Single prediction
        @app.route('/predict/<model_name>', methods=['POST'])
        def predict(model_name: str):
            """Make a single prediction."""
            data = request.get_json()

            if not data:
                return jsonify({'error': 'No features provided'}), 400

            features = data.get('features', data)
            use_cache = data.get('use_cache', True)

            result = self.server.predict(model_name, features, use_cache)

            if result is None:
                return jsonify(
                    {
                        'error': 'Prediction failed',
                        'model': model_name,
                    },
                ), 500

            return jsonify(
                {
                    'success': True,
                    'model': model_name,
                    'result': result,
                },
            )

        # Batch prediction
        @app.route('/predict/<model_name>/batch', methods=['POST'])
        def batch_predict(model_name: str):
            """Make batch predictions."""
            data = request.get_json()

            if not data or 'features_list' not in data:
                return jsonify({'error': 'No features_list provided'}), 400

            features_list = data['features_list']
            use_cache = data.get('use_cache', True)

            results = []
            errors = []

            for i, features in enumerate(features_list):
                result = self.server.predict(model_name, features, use_cache)
                if result:
                    results.append(
                        {
                            'index': i,
                            'result': result,
                        },
                    )
                else:
                    errors.append(
                        {
                            'index': i,
                            'error': 'Prediction failed',
                        },
                    )

            return jsonify(
                {
                    'success': True,
                    'model': model_name,
                    'count': len(features_list),
                    'successful': len(results),
                    'failed': len(errors),
                    'results': results,
                    'errors': errors,
                },
            )

        # Cache stats
        @app.route('/cache/stats', methods=['GET'])
        def cache_stats():
            """Get cache statistics."""
            if self.server._cache:
                return jsonify(self.server._cache.get_stats())
            return jsonify({'error': 'Cache not enabled'}), 404

        # Clear cache
        @app.route('/cache/clear', methods=['POST'])
        def clear_cache():
            """Clear prediction cache."""
            if self.server._cache:
                self.server._cache.clear()
                return jsonify({'success': True, 'message': 'Cache cleared'})
            return jsonify({'error': 'Cache not enabled'}), 404

        # Server stats
        @app.route('/stats', methods=['GET'])
        def stats():
            """Get server statistics."""
            return jsonify(self.server.get_stats())

        # Reload models
        @app.route('/reload', methods=['POST'])
        def reload_models():
            """Reload all models."""
            results = self.server.reload_all()
            return jsonify(
                {
                    'success': True,
                    'results': results,
                },
            )

        return app


def create_app(db_connection=None, model_dir: str = 'models') -> Flask:
    """Create and configure Flask app.

    Args:
        db_connection: Database connection
        model_dir: Model directory

    Returns:
        Configured Flask app
    """
    server = ModelServer(
        db_connection=db_connection,
        model_dir=model_dir,
        enable_cache=True,
    )

    # Load default models
    server.load_model('next_run', 'latest')
    server.load_model('pa_outcome', 'latest')

    api = PredictionAPI(model_server=server)
    return api.create_app()


# For direct execution
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Prediction API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind')
    parser.add_argument('--model-dir', default='models', help='Model directory')
    parser.add_argument('--debug', action='store_true', help='Debug mode')

    args = parser.parse_args()

    # Create app
    app = create_app(model_dir=args.model_dir)

    # Run
    app.run(host=args.host, port=args.port, debug=args.debug)
