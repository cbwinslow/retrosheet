"""
Integrated Retrosheet data source demonstrating the comprehensive error handling architecture.

This example shows how to apply the integration layer to existing baseball components
for intelligent error handling, monitoring, and benchmarking.
"""

import asyncio
from typing import Dict, Any, Optional

from baseball.core.integration_layer import IntegratedDataSource
from baseball.core.error_architecture import ErrorContext, ErrorCategory
from baseball.core.system_monitoring import system_monitor
from baseball.sources.retrosheet import RetrosheetSource


class IntegratedRetrosheetSource(IntegratedDataSource):
    """Retrosheet data source with full integration"""
    
    def __init__(self):
        super().__init__("retrosheet_integrated")
        self.retrosheet_source: Optional[RetrosheetSource] = None
        self._setup_error_context()
    
    def _setup_error_context(self):
        """Setup error context for this component"""
        self.error_context = ErrorContext(
            command_name="retrosheet",
            operation_name="data_ingestion",
            category=ErrorCategory.DATA_SOURCE,
            metadata={
                "source_type": "retrosheet",
                "integration_version": "1.0.0"
            }
        )
    
    async def initialize(self, config: Dict[str, Any] = None):
        """Initialize the integrated retrosheet source"""
        await self.register_with_integration(config or {})
        
        # Initialize the underlying retrosheet source
        self.retrosheet_source = RetrosheetSource()
        
        return True
    
    async def download(self, years: list = None, **kwargs):
        """Download retrosheet data with full integration"""
        if not self.retrosheet_source:
            raise RuntimeError("Retrosheet source not initialized")
        
        # Use the integration layer for automatic error handling and monitoring
        integration = self.get_integration_layer()
        
        return await integration.execute_component_operation(
            self.name, "download", 
            self._download_with_monitoring, years, **kwargs
        )
    
    async def _download_with_monitoring(self, years: list = None, **kwargs):
        """Internal download method with monitoring"""
        self.start_benchmark("retrosheet_download")
        
        try:
            # Record operation start
            await system_monitor.record_operation_performance(
                "retrosheet_download", 0, 0, 0
            )
            
            # Execute actual download
            result = await self.retrosheet_source.download(years=years, **kwargs)
            
            # Record success metrics
            duration_ms = self.end_benchmark("retrosheet_download")
            rows_processed = len(result) if isinstance(result, list) else 0
            
            await system_monitor.record_operation_performance(
                "retrosheet_download", duration_ms, rows_processed, 0
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            duration_ms = self.end_benchmark("retrosheet_download")
            await system_monitor.record_operation_performance(
                "retrosheet_download", duration_ms, 0, 1
            )
            
            # Re-raise for intelligent error handling
            raise e
    
    async def ingest(self, data: Any, **kwargs):
        """Ingest retrosheet data with full integration"""
        if not self.retrosheet_source:
            raise RuntimeError("Retrosheet source not initialized")
        
        integration = self.get_integration_layer()
        
        return await integration.execute_component_operation(
            self.name, "ingest",
            self._ingest_with_monitoring, data, **kwargs
        )
    
    async def _ingest_with_monitoring(self, data: Any, **kwargs):
        """Internal ingest method with monitoring"""
        self.start_benchmark("retrosheet_ingest")
        
        try:
            # Record operation start
            await system_monitor.record_operation_performance(
                "retrosheet_ingest", 0, 0, 0
            )
            
            # Execute actual ingestion
            result = await self.retrosheet_source.ingest(data, **kwargs)
            
            # Record success metrics
            duration_ms = self.end_benchmark("retrosheet_ingest")
            rows_processed = len(data) if hasattr(data, '__len__') else 0
            
            await system_monitor.record_operation_performance(
                "retrosheet_ingest", duration_ms, rows_processed, 0
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            duration_ms = self.end_benchmark("retrosheet_ingest")
            await system_monitor.record_operation_performance(
                "retrosheet_ingest", duration_ms, 0, 1
            )
            
            # Re-raise for intelligent error handling
            raise e
    
    async def get_seasons(self) -> list:
        """Get available seasons with integration"""
        if not self.retrosheet_source:
            raise RuntimeError("Retrosheet source not initialized")
        
        return await self.retrosheet_source.get_seasons()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check with monitoring"""
        self.start_benchmark("retrosheet_health_check")
        
        try:
            # Test basic connectivity
            seasons = await self.get_seasons()
            
            # Get system metrics
            health_status = await system_monitor.generate_health_report()
            
            # Get component performance stats
            download_stats = self.get_benchmark_stats("retrosheet_download")
            ingest_stats = self.get_benchmark_stats("retrosheet_ingest")
            
            health_result = {
                "component": "retrosheet_integrated",
                "status": "healthy" if seasons else "degraded",
                "available_seasons": len(seasons),
                "system_health": health_status,
                "performance_stats": {
                    "download": download_stats,
                    "ingest": ingest_stats
                },
                "timestamp": system_monitor.get_system_metrics()[-1].timestamp if system_monitor.get_system_metrics() else None
            }
            
            self.end_benchmark("retrosheet_health_check")
            return health_result
            
        except Exception as e:
            self.end_benchmark("retrosheet_health_check")
            return {
                "component": "retrosheet_integrated",
                "status": "unhealthy",
                "error": str(e),
                "timestamp": system_monitor.get_system_metrics()[-1].timestamp if system_monitor.get_system_metrics() else None
            }


# Factory function for creating integrated retrosheet source
async def create_integrated_retrosheet(config: Dict[str, Any] = None) -> IntegratedRetrosheetSource:
    """Create an integrated retrosheet source with full error handling"""
    from baseball.core.integration_layer import ComponentFactory
    
    source = await ComponentFactory.create_data_source(
        IntegratedRetrosheetSource, "retrosheet_integrated", config
    )
    
    await source.initialize(config)
    
    return source


# Example usage demonstrating the full integration
async def demonstrate_integrated_retrosheet():
    """Demonstrate the integrated retrosheet source"""
    print("Initializing baseball integration system...")
    
    # Initialize the integration system
    from baseball.core.integration_layer import initialize_baseball_integration
    await initialize_baseball_integration()
    
    print("Creating integrated retrosheet source...")
    
    # Create integrated retrosheet source
    retrosheet = await create_integrated_retrosheet({
        "cache_enabled": True,
        "retry_attempts": 3,
        "timeout_seconds": 30
    })
    
    print("Performing health check...")
    
    # Perform health check
    health = await retrosheet.health_check()
    print(f"Health status: {health['status']}")
    
    print("Getting available seasons...")
    
    # Get available seasons
    try:
        seasons = await retrosheet.get_seasons()
        print(f"Available seasons: {len(seasons)}")
        
        if seasons:
            print(f"Sample seasons: {seasons[:3]}")
            
            print("Downloading data for recent season...")
            
            # Download data for most recent season
            recent_season = max(seasons)
            download_result = await retrosheet.download(years=[recent_season])
            print(f"Downloaded {len(download_result) if download_result else 0} records")
            
            if download_result:
                print("Ingesting data...")
                
                # Ingest the downloaded data
                ingest_result = await retrosheet.ingest(download_result)
                print(f"Ingestion completed: {ingest_result}")
    
    except Exception as e:
        print(f"Error during demonstration: {e}")
    
    print("Generating system report...")
    
    # Generate comprehensive system report
    from baseball.core.integration_layer import get_integration_layer
    integration = get_integration_layer()
    system_status = await integration.get_system_status()
    
    print("System Status Summary:")
    print(f"- Integration active: {system_status['integration_layer']['active']}")
    print(f"- Registered components: {system_status['integration_layer']['registered_components']}")
    print(f"- Total plugins: {system_status['plugin_system']['total_plugins']}")
    
    if 'system_monitoring' in system_status:
        monitoring = system_status['system_monitoring']
        if 'system_metrics' in monitoring:
            metrics = monitoring['system_metrics']
            print(f"- CPU usage: {metrics.get('cpu_usage_percent', 0):.1f}%")
            print(f"- Memory usage: {metrics.get('memory_usage_mb', 0):.1f}MB")
    
    print("Demonstration completed.")


if __name__ == "__main__":
    asyncio.run(demonstrate_integrated_retrosheet())
