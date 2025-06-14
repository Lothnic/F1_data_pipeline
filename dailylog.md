# 📅 F1 Data Pipeline - Daily Log

## 🚀 Progress

### 📅 June 14, 2024
**🕒 9:00 AM - 5:00 PM**  
- [ ] Worked on data extraction script
- [ ] Implemented GCS upload functionality but had rate limit issues
- [ ] Added error handling for API calls using time.sleep()

**Technical Notes:**
- Successfully extracted session data
- Implemented batch processing for better performance

**Blockers/Issues:**  
⚠️ Rate limit issues

**Next Steps:**
- [ ] Test data transformation pipeline
- [ ] Add data validation
- [ ] Document the extraction process

### 📅 June 13, 2024
**🕒 10:00 AM - 12:00 PM**  
- [x] Initial setup of FastF1 library
- [x] Basic data extraction working
- [x] Created GCP Account and connected to it using cli and python code google cloud storage library.
- [x] Reduced extraction time by 90%

**Technical Notes:**
- Successfully connected to FastF1 API
- Extracted lap time data for initial analysis

**Blockers/Issues:**  
⚠️ Need to resolve GCS authentication - Done

**Next Steps:**
- [ ] All Data Ingestion
- [ ] Implement data transformation
- [ ] Add error handling


## 📊 Weekly Summary
### Week 24 (Jun 10-16, 2024)
- **Goals:**
  - [ ] Basic data pipeline setup
  - [ ] Initial data analysis

## 🔗 Useful Links
- [FastF1 Documentation](https://docs.fastf1.dev/)
- [GCP Storage Documentation](https://cloud.google.com/storage/docs)