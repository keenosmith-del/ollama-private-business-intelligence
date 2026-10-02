-- Questions are private analysis data, not request logs. Legacy history remains readable.
ALTER TABLE ai_analysis_requests ADD COLUMN question text;
