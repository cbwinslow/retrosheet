#!/usr/bin/env python3
"""
Check model registry and predictions status.
"""

from sqlalchemy import create_engine, text

engine = create_engine('postgresql://cbwinslow@localhost:5432/retrosheet')

with engine.connect() as conn:
    # Check model registry schema
    result = conn.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'models' AND table_name = 'model_registry' 
        ORDER BY ordinal_position
    """))
    print('=== MODEL REGISTRY SCHEMA ===')
    for row in result:
        print(f'{row[0]}: {row[1]}')
    
    print()
    
    # Check model registry data
    result = conn.execute(text('SELECT * FROM models.model_registry LIMIT 10'))
    print('=== MODEL REGISTRY DATA ===')
    columns = result.keys()
    for row in result:
        print(dict(zip(columns, row)))
    
    print()
    
    # Check if predictions table exists
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'predictions' AND table_name = 'pa_predictions'
        )
    """))
    predictions_exists = result.scalar()
    print(f'=== PREDICTIONS TABLE EXISTS ===')
    print(f'predictions.pa_predictions: {predictions_exists}')
    
    if predictions_exists:
        result = conn.execute(text('SELECT COUNT(*) FROM predictions.pa_predictions'))
        print(f'Total PA predictions: {result.scalar()}')
        
        result = conn.execute(text("""
            SELECT prediction_date, COUNT(*) 
            FROM predictions.pa_predictions 
            GROUP BY prediction_date 
            ORDER BY prediction_date DESC 
            LIMIT 5
        """))
        print('Recent predictions by date:')
        for row in result:
            print(f'  {row[0]}: {row[1]} predictions')
