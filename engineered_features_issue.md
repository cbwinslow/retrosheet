## 🎯 Objective
Complete the population of features_pitch.engineered_features table with tiered outcomes and derived physics features from the populated base_features table.

## 📋 Task Breakdown
- [x] Engineered features table schema created
- [x] Initial test population (100 rows completed successfully)
- [x] Parameter issues fixed in populate_engineered_features.py
- [ ] Fix remaining parameter tuple issue in batch processing
- [ ] Populate full engineered_features table from base_features
- [ ] Implement velocity categorization and percentiles
- [ ] Add zone classification and distance metrics
- [ ] Create outcome binaries for classification targets
- [ ] Calculate derived physics metrics (break, approach angle, spin efficiency)
- [ ] Add sequence context features
- [ ] Validate engineered features data quality

## 🔧 Technical Requirements
- Use script: scripts/pitch_data/populate_engineered_features.py
- Process all 20.1M rows from base_features
- Implement tiered outcomes: {ball, strike, ball_in_play}
- Create derived physics features from Statcast data
- Batch processing with proper parameter handling
- Maintain data lineage and metadata

## 🎯 Success Criteria
- Engineered_features table fully populated with 20.1M rows
- All tiered outcomes correctly calculated
- Velocity categorization implemented (slow, medium, fast, elite)
- Zone classification complete (heart, shadow, chase, waste)
- Derived physics metrics calculated
- Data quality score > 95%
- Processing rate > 10,000 rows/sec

## 🔗 Dependencies
- Base_features table populated (✓ 20.1M rows)
- Database connectivity established (✓)
- Engineered features schema ready (✓)
- Script parameter fixes needed (⏳)

## 📅 Timeline
Target completion: Within 48 hours

## 🚀 Implementation Strategy
1. Fix parameter tuple issue in populate_engineered_features.py
2. Test with small batch (1,000 rows)
3. Scale to full dataset processing
4. Implement all engineered feature calculations
5. Validate data quality and completeness
6. Document processing results

## 📊 Current Status
- Base features: 20.1M rows populated
- Engineered features test: 100 rows successful
- Script issues: Parameter tuple IndexError needs fixing
- Database connectivity: Working
- Schema: Ready and validated

## 🔍 Technical Issues to Resolve
- Fix IndexError: tuple index out of range in line 350
- Ensure proper parameter passing for batch processing
- Optimize processing for large dataset (20.1M rows)
- Implement all engineered feature calculations

## 📈 Processing Requirements
- Target: 20.1M rows from base_features
- Batch size: 10,000 rows per batch
- Estimated time: 30-60 minutes for full population
- Memory usage: Optimize for large dataset processing
