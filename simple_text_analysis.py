import re
import logging
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EnhancedGrammarChecker:
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
            "you is": "you are",
            
            # Common verb errors
            "store": "live",
            "buyed": "bought",
            "goed": "went",
            "eated": "ate",
            "runned": "ran",
            "speaked": "spoke",
            "teached": "taught",
            "catched": "caught",
            "bringed": "brought",
            "thinked": "thought",
            
            # Preposition errors
            "in home": "at home",
            "on home": "at home",
            "on japan": "in Japan",
            "at japan": "in Japan",
            "in school": "at school",
            "on school": "at school",
            
            # Article errors
            "a apple": "an apple",
            "a hour": "an hour",
            "an book": "a book",
            "an university": "a university",
            "a european": "a European",
            
            # Common speech recognition errors
            "i name": "My name",
            "me name": "My name",
            "your name": "your name",
            "his name": "his name", 
            "her name": "her name",
            "our name": "our name",
            "their name": "their name",
            
            # Additional common errors
            "should of": "should have",
            "could of": "could have",
            "would of": "would have",
            "must of": "must have",
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
            "cannot": "can't",
            "could not": "couldn't",
            "should not": "shouldn't",
            "would not": "wouldn't"
        }
    
    def check_with_languagetool(self, text):
        """Use LanguageTool API for comprehensive grammar checking"""
        try:
            response = requests.post(
                'https://api.languagetool.org/v2/check',
                data={
                    'text': text,
                    'language': 'en-US'
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"LanguageTool API returned status {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"LanguageTool API error: {e}")
            return None
    
    def correct_text(self, text):
        """Enhanced correction using both rule-based and API-based checking"""
        if not text or not text.strip():
            return text, [], 0, "No text provided"
        
        original = text.strip()
        corrections = []
        
        # Step 1: Apply rule-based corrections
        corrected = self._fix_capitalization(original)
        corrected, rule_corrections = self._apply_rule_corrections(corrected)
        corrections.extend(rule_corrections)
        
        # Step 2: Use LanguageTool API for additional corrections
        api_result = self.check_with_languagetool(corrected)
        if api_result and 'matches' in api_result:
            api_corrections = self._process_api_results(corrected, api_result['matches'])
            corrections.extend(api_corrections)
            
            # Apply API corrections
            for correction in api_corrections:
                corrected = self._apply_api_correction(corrected, correction)
        
        # Final cleanup
        corrected = self._fix_sentence_end(corrected)
        corrected = self._fix_contractions(corrected)
        
        total_errors = len(corrections)
        
        # Generate analysis summary
        analysis_summary = self._generate_analysis_summary(original, corrected, total_errors)
        
        return corrected, corrections, total_errors, analysis_summary
    
    def _apply_rule_corrections(self, text):
        """Apply rule-based corrections"""
        corrections = []
        corrected = text
        
        for wrong, right in self.common_errors.items():
            if self._contains_word(corrected, wrong):
                before_correction = corrected
                corrected = self._replace_word(corrected, wrong, right)
                if before_correction != corrected:
                    wrong_word = self._extract_word(before_correction, wrong)
                    corrections.append({
                        'original': wrong_word,
                        'corrected': right,
                        'message': f'"{wrong_word}" should be "{right}"',
                        'category': 'GRAMMAR',
                        'type': 'rule_based'
                    })
        
        return corrected, corrections
    
    def _process_api_results(self, text, matches):
        """Process LanguageTool API results"""
        corrections = []
        
        for match in matches:
            if match.get('replacements'):
                best_replacement = match['replacements'][0]['value']
                wrong_text = text[match['offset']:match['offset'] + match['length']]
                
                # Avoid duplicates with rule-based corrections
                if not any(corr['original'] == wrong_text and corr['corrected'] == best_replacement 
                          for corr in corrections):
                    corrections.append({
                        'original': wrong_text,
                        'corrected': best_replacement,
                        'message': match.get('message', 'Grammar error'),
                        'category': match.get('rule', {}).get('category', 'GRAMMAR'),
                        'type': 'api_based'
                    })
        
        return corrections
    
    def _apply_api_correction(self, text, correction):
        """Apply API-based correction to text"""
        return text.replace(correction['original'], correction['corrected'])
    
    def _generate_analysis_summary(self, original, corrected, total_errors):
        """Generate comprehensive analysis summary"""
        if total_errors == 0:
            return "Excellent! Your sentence is grammatically correct."
        else:
            return f"This sentence has {total_errors} error(s). The corrected version is: \"{corrected}\""
    
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
        corrected = text
        for wrong, correct in self.contractions.items():
            if self._contains_word(corrected, wrong):
                corrected = self._replace_word(corrected, wrong, correct)
        return corrected
    
    def _fix_sentence_end(self, text):
        """Add period if missing"""
        if text and not text.endswith(('.', '!', '?')):
            text += '.'
        return text

# Initialize the enhanced grammar checker
grammar_checker = EnhancedGrammarChecker()

@app.route('/analyze-text', methods=['POST'])
def analyze_text_endpoint():
    """Enhanced endpoint for analyzing text with hybrid approach"""
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
        
        # Analyze the text with enhanced checker
        corrected_text, corrections, wrong_word_count, analysis_summary = grammar_checker.correct_text(text)
        
        # Calculate confidence
        total_words = len(text.split())
        confidence = max(0.0, 1.0 - (wrong_word_count / max(1, total_words)))
        
        result = {
            'original_sentence': text,
            'corrected_sentence': corrected_text,
            'wrong_word_count': wrong_word_count,
            'corrections': corrections,
            'confidence': round(confidence, 2),
            'analysis_summary': analysis_summary,
            'total_words': total_words
        }
        
        logger.info(f"Analysis complete. Found {wrong_word_count} errors.")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in analyze-text endpoint: {str(e)}")
        return jsonify({
            'error': f'Analysis failed: {str(e)}',
            'corrected_sentence': data.get('text', ''),
            'wrong_word_count': 0,
            'corrections': [],
            'analysis_summary': 'Analysis failed due to an error'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'enhanced_grammar_checker'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)