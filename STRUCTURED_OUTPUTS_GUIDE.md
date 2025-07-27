# Structured Outputs Implementation Guide

## Overview

This project has been updated to use Azure OpenAI's structured outputs feature for improved data consistency, type safety, and better analytics capabilities. The implementation follows the [Microsoft Azure documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs?tabs=python%2Cdotnet-keys&pivots=programming-language-python) for structured outputs.

## Key Changes

### 1. Pydantic Models for Type Safety

The system now uses Pydantic models to define the structure of AI-generated content:

```python
class BrainBeeQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    explanation: Optional[str] = None
    category: Optional[str] = None

class QuestionEvaluation(BaseModel):
    question_score: int
    answer_score: int
    justification: str

class UserFeedback(BaseModel):
    question: str
    user_answer: str
    correct_answer: str
    evaluation: Optional[str] = None
    category: Optional[str] = None
    is_correct: bool
```

### 2. Structured Question Generation

Instead of parsing free-form text responses, the system now uses structured outputs:

```python
response = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[...],
    response_format=BrainBeeQuestion,
    temperature=0.8,
    top_p=0.9,
)
```

### 3. Enhanced Supabase Schema

The database schema has been updated to support structured data:

```sql
CREATE TABLE IF NOT EXISTS feedback_scores (
    id BIGSERIAL PRIMARY KEY,
    question TEXT NOT NULL,
    user_answer TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    evaluation TEXT,
    category TEXT,
    is_correct BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Benefits

### 1. **Data Consistency**
- Structured outputs ensure all AI responses follow the same format
- No more parsing errors from inconsistent text responses
- Guaranteed JSON structure for database storage

### 2. **Type Safety**
- Pydantic models provide runtime type validation
- IDE support for better development experience
- Automatic error handling for malformed data

### 3. **Better Analytics**
- Structured data enables complex queries and analytics
- Category-based performance tracking
- Accuracy metrics per neuroscience topic

### 4. **Improved Reliability**
- Fallback mechanisms when structured outputs fail
- Graceful degradation to traditional completion
- Better error handling and logging

## Implementation Details

### Question Generation Process

1. **Content Selection**: Uses `simple_fallback.py` for intelligent content selection
2. **Structured Prompting**: Sends prompts designed for structured output
3. **Response Parsing**: Directly extracts structured data without text parsing
4. **Fallback Handling**: Falls back to traditional completion if structured outputs fail

### Feedback Reporting

1. **Structured Evaluation**: Uses `QuestionEvaluation` model for consistent scoring
2. **Category Detection**: Automatically determines neuroscience category
3. **Database Storage**: Stores structured feedback with additional metadata
4. **Analytics Ready**: Data is immediately available for analysis

### Database Schema Updates

The new schema includes:
- `category`: Neuroscience topic category
- `is_correct`: Boolean flag for correct/incorrect answers
- `evaluation`: Structured evaluation results
- Analytics view for performance tracking

## Usage Examples

### Running Analytics

```bash
python analytics_example.py
```

This will generate a comprehensive analytics report including:
- Performance by category
- Overall accuracy metrics
- Recent question analysis
- Data export for external analysis

### Database Queries

```sql
-- Get performance by category
SELECT category, 
       COUNT(*) as total_questions,
       AVG(CASE WHEN is_correct THEN 1.0 ELSE 0.0 END) as accuracy
FROM feedback_scores 
GROUP BY category;

-- Get recent questions with evaluations
SELECT question, user_answer, correct_answer, is_correct, evaluation
FROM feedback_scores 
ORDER BY created_at DESC 
LIMIT 10;
```

## Migration Guide

### For Existing Users

1. **Update Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Update Database Schema**:
   ```sql
   -- Run the updated supabase_setup.sql
   ```

3. **Environment Variables**:
   Ensure your `.env` file includes:
   ```
   AZURE_OPENAI_API_KEY=your_key
   AZURE_OPENAI_ENOINT=your_endpoint
   SUPABASE_URL=your_url
   SUPABASE_ANON_KEY=your_key
   ```

### For New Users

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Up Database**:
   - Create a Supabase project
   - Run the SQL from `supabase_setup.sql`
   - Configure environment variables

3. **Run the Application**:
   ```bash
   python app.py
   ```

## Error Handling

The system includes robust error handling:

1. **Structured Output Failures**: Falls back to traditional completion
2. **Database Errors**: Graceful degradation to session-only storage
3. **API Errors**: Comprehensive logging and user feedback
4. **Validation Errors**: Type checking with Pydantic models

## Performance Considerations

### Structured Outputs vs Traditional Completion

- **Pros**: Better data consistency, type safety, easier parsing
- **Cons**: Slightly higher latency, requires newer API version
- **Mitigation**: Fallback mechanisms ensure reliability

### Database Performance

- New indexes on `category` and `is_correct` fields
- Analytics view for efficient querying
- JSONB storage for flexible session data

## Future Enhancements

1. **Advanced Analytics**: Machine learning insights from structured data
2. **Personalization**: User-specific question generation based on performance
3. **A/B Testing**: Structured data enables easy experiment tracking
4. **Export Features**: Rich data export for external analysis tools

## Troubleshooting

### Common Issues

1. **Structured Output Errors**:
   - Check API version compatibility
   - Verify model deployment supports structured outputs
   - Review Pydantic model definitions

2. **Database Connection Issues**:
   - Verify Supabase credentials
   - Check network connectivity
   - Review database schema

3. **Performance Issues**:
   - Monitor API response times
   - Check database query performance
   - Review caching strategies

### Debug Mode

Enable detailed logging by setting:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Conclusion

The structured outputs implementation provides significant improvements in data quality, reliability, and analytics capabilities. The system maintains backward compatibility while offering enhanced features for both users and administrators.

For more information about Azure OpenAI structured outputs, refer to the [official documentation](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/structured-outputs?tabs=python%2Cdotnet-keys&pivots=programming-language-python). 