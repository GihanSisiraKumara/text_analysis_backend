import re
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleGrammarChecker:
    def __init__(self):
        self.common_errors = {
            # Subject-verb agreement
            "i is": "I am",
            "i are": "I am", 
            "he are": "he is",
            "she are": "she is",
            "it are": "it is",
            "we is": "we are",
            "they is": "they are",
            
            # Common word errors
            "store": "live",
            "buyed": "bought",
            "goed": "went",
            "eated": "ate",
            "runned": "ran",
            "speaked": "spoke",
            
            # Preposition errors
            "in home": "at home",
            "on home": "at home",
            "on japan": "in Japan",
            "at japan": "in Japan",
            
            # Article errors
            "a apple": "an apple",
            "a hour": "an hour",
            "an book": "a book",
            "an university": "a university",
            
            # Common speech recognition errors
            "i name": "My name",
            "me name": "My name",
            "your name": "your name",  # keep but handle case
            "his name": "his name",
            "her name": "her name",
            "our name": "our name",
            "their name": "their name"
        }
        
        self.contractions = {
            "i am": "I'm",
            "you are": "you're",
            "he is": "he's",
            "she is": "she's",
            "it is": "it's",
            "we are": "we're",
            "they are": "they're",
            "is not": "isn't",
            "are not": "aren't",
            "do not": "don't",
            "does not": "doesn't",
            "did not": "didn't",
            "have not": "haven't",
            "has not": "hasn't",
            "had not": "hadn't",
            "will not": "won't",
            "cannot": "can't"
        }
    
    def correct_text(self, text):
        """Main function to correct text"""
        if not text or not text.strip():
            return text, [], 0
        
        original = text.strip()
        corrections = []
        corrected = original
        
        # Fix capitalization first
        corrected = self._fix_capitalization(corrected)
        
        # Fix common errors
        for wrong, right in self.common_errors.items():
            if self._contains_word(corrected, wrong):
                before_correction = corrected
                corrected = self._replace_word(corrected, wrong, right)
                if before_correction != corrected:
                    # Extract the actual word that was changed
                    wrong_word = self._extract_word(before_correction, wrong)
                    corrections.append({
                        'original': wrong_word,
                        'corrected': right,
                        'message': f'"{right}" is more appropriate than "{wrong_word}"',
                        'category': 'GRAMMAR'
                    })
        
        # Fix contractions
        corrected = self._fix_contractions(corrected)
        
        # Ensure proper sentence ending
        corrected = self._fix_sentence_end(corrected)
        
        return corrected, corrections, len(corrections)
    
    def _contains_word(self, text, word):
        """Check if text contains a word (case insensitive)"""
        return re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE) is not None
    
    def _replace_word(self, text, wrong, right):
        """Replace word preserving case"""
        pattern = re.compile(r'\b' + re.escape(wrong) + r'\b', re.IGNORECASE)
        return pattern.sub(lambda m: self._match_case(right, m.group()), text)
    
    def _extract_word(self, text, word):
        """Extract the actual word from text"""
        match = re.search(r'\b' + re.escape(word) + r'\b', text, re.IGNORECASE)
        return match.group() if match else word
    
    def _match_case(self, replacement, original):
        """Match the case of the replacement to the original"""
        if original.isupper():
            return replacement.upper()
        elif original.istitle():
            return replacement.title()
        else:
            return replacement.lower()
    
    def _fix_capitalization(self, text):
        """Capitalize first letter of sentence"""
        if text and len(text) > 0:
            text = text[0].upper() + text[1:]
        return text
    
    def _fix_contractions(self, text):
        """Fix common contractions"""
        corrected = text.lower()
        for wrong, correct in self.contractions.items():
            corrected = re.sub(r'\b' + wrong + r'\b', correct, corrected)
        return self._fix_capitalization(corrected)
    
    def _fix_sentence_end(self, text):
        """Add period if missing"""
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        return text

# Initialize the grammar checker
grammar_checker = SimpleGrammarChecker()

@app.route('/analyze-text', methods=['POST'])
def analyze_text_endpoint():
    """Endpoint for analyzing text for grammatical errors"""
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
        corrected_text, corrections, wrong_word_count = grammar_checker.correct_text(text)
        
        # Calculate confidence
        total_words = len(text.split())
        confidence = max(0.0, 1.0 - (wrong_word_count / max(1, total_words)))
        
        result = {
            'corrected_sentence': corrected_text,
            'wrong_word_count': wrong_word_count,
            'corrections': corrections,
            'confidence': round(confidence, 2),
            'original_sentence': text
        }
        
        logger.info(f"Analysis complete. Found {wrong_word_count} errors.")
        
        return jsonify(result)
        
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
        'service': 'simple_grammar_checker'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)