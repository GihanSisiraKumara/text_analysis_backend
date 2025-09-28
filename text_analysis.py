import re
import spacy
import language_tool_python
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load English language model for spaCy
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("spaCy English model loaded successfully")
except OSError:
    logger.error("spaCy English model not found. Please install it using: python -m spacy download en_core_web_sm")
    nlp = None

# Initialize LanguageTool for grammar checking
try:
    tool = language_tool_python.LanguageTool('en-US')
    logger.info("LanguageTool initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize LanguageTool: {e}")
    tool = None

def correct_common_contractions(text):
    """Fix common contraction errors that might occur in speech"""
    contractions = {
        "i am": "I'm",
        "i will": "I'll",
        "i have": "I've",
        "you are": "you're",
        "he is": "he's",
        "she is": "she's",
        "it is": "it's",
        "we are": "we're",
        "they are": "they're",
        "is not": "isn't",
        "are not": "aren't",
        "was not": "wasn't",
        "were not": "weren't",
        "do not": "don't",
        "does not": "doesn't",
        "did not": "didn't",
        "have not": "haven't",
        "has not": "hasn't",
        "had not": "hadn't",
        "will not": "won't",
        "would not": "wouldn't",
        "should not": "shouldn't",
        "could not": "couldn't",
        "cannot": "can't"
    }
    
    corrected_text = text.lower()
    for wrong, correct in contractions.items():
        corrected_text = re.sub(r'\b' + wrong + r'\b', correct, corrected_text)
    
    # Capitalize first letter
    if corrected_text:
        corrected_text = corrected_text[0].upper() + corrected_text[1:]
    
    return corrected_text

def analyze_grammar_and_words(text):
    """
    Analyze text for grammatical errors and incorrect word usage
    Returns corrected text, error count, and detailed corrections
    """
    if not text or not text.strip():
        return {
            'corrected_sentence': text,
            'wrong_word_count': 0,
            'corrections': [],
            'confidence': 1.0
        }
    
    original_text = text.strip()
    corrections = []
    
    # Step 1: Use LanguageTool for grammar checking
    grammar_corrections = []
    if tool:
        try:
            matches = tool.check(original_text)
            for match in matches:
                if match.replacements:
                    grammar_corrections.append({
                        'original': match.context[match.offset:match.offset + match.errorLength],
                        'corrected': match.replacements[0],
                        'message': match.message,
                        'category': match.category
                    })
        except Exception as e:
            logger.error(f"LanguageTool error: {e}")
    
    # Step 2: Common word error patterns (you can expand this dictionary)
    common_errors = {
        # Subject-verb agreement
        "i is": "I am",
        "i are": "I am",
        "he are": "he is",
        "she are": "she is",
        "it are": "it is",
        "we is": "we are",
        "they is": "they are",
        
        # Common mispronunciations that lead to wrong words
        "store": "live",
        "buyed": "bought",
        "goed": "went",
        "eated": "ate",
        "runned": "ran",
        
        # Preposition errors
        "in japan": "in Japan",
        "on japan": "in Japan",
        "at japan": "in Japan",
        "in home": "at home",
        "on home": "at home",
        
        # Article errors
        "a apple": "an apple",
        "a hour": "an hour",
        "an book": "a book",
        "an university": "a university",
    }
    
    # Step 3: Fix common patterns
    corrected_text = original_text
    
    # Fix "I name" -> "My name"
    if re.search(r'\bI name\b', corrected_text, re.IGNORECASE):
        corrected_text = re.sub(r'\bI name\b', 'My name', corrected_text, flags=re.IGNORECASE)
        corrections.append({
            'original': 'I',
            'corrected': 'My',
            'message': 'Use "My" instead of "I" before nouns',
            'category': 'PRONOUN_USAGE'
        })
    
    # Apply common error corrections
    for wrong, right in common_errors.items():
        pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
        if pattern.search(corrected_text):
            original_word = pattern.search(corrected_text).group()
            corrected_text = pattern.sub(right, corrected_text)
            
            # Only add to corrections if it actually changed
            if original_word.lower() != right.lower():
                corrections.append({
                    'original': original_word,
                    'corrected': right,
                    'message': f'"{right}" is more appropriate in this context',
                    'category': 'WORD_USAGE'
                })
    
    # Step 4: Apply grammar corrections from LanguageTool
    temp_corrected = corrected_text
    for gc in grammar_corrections:
        if gc['original'] in temp_corrected:
            temp_corrected = temp_corrected.replace(gc['original'], gc['corrected'], 1)
            corrections.append(gc)
    
    corrected_text = temp_corrected
    
    # Step 5: Fix capitalization and punctuation
    corrected_text = correct_common_contractions(corrected_text)
    
    # Ensure proper sentence capitalization
    if corrected_text and len(corrected_text) > 0:
        corrected_text = corrected_text[0].upper() + corrected_text[1:]
    
    # Add period if missing
    if corrected_text and not corrected_text.endswith(('.', '!', '?')):
        corrected_text += '.'
    
    # Step 6: Remove duplicates from corrections
    unique_corrections = []
    seen_corrections = set()
    
    for correction in corrections:
        key = (correction['original'].lower(), correction['corrected'].lower())
        if key not in seen_corrections:
            unique_corrections.append(correction)
            seen_corrections.add(key)
    
    # Calculate confidence score
    total_words = len(original_text.split())
    wrong_word_count = len(unique_corrections)
    confidence = max(0.0, 1.0 - (wrong_word_count / max(1, total_words)))
    
    return {
        'corrected_sentence': corrected_text,
        'wrong_word_count': wrong_word_count,
        'corrections': unique_corrections,
        'confidence': round(confidence, 2),
        'original_sentence': original_text
    }

@app.route('/analyze-text', methods=['POST'])
def analyze_text_endpoint():
    """
    Endpoint for analyzing text for grammatical errors
    Expected JSON: {'text': 'string to analyze', 'language': 'en'}
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        text = data.get('text', '').strip()
        language = data.get('language', 'en')
        
        if not text:
            return jsonify({'error': 'No text provided for analysis'}), 400
        
        if language != 'en':
            return jsonify({'error': 'Only English language is currently supported'}), 400
        
        logger.info(f"Analyzing text: {text}")
        
        # Analyze the text
        analysis_result = analyze_grammar_and_words(text)
        
        logger.info(f"Analysis complete. Found {analysis_result['wrong_word_count']} errors.")
        
        return jsonify(analysis_result)
        
    except Exception as e:
        logger.error(f"Error in analyze-text endpoint: {str(e)}")
        return jsonify({
            'error': f'Analysis failed: {str(e)}',
            'corrected_sentence': data.get('text', ''),
            'wrong_word_count': 0,
            'corrections': []
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'services': {
            'language_tool': tool is not None,
            'spacy': nlp is not None
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)