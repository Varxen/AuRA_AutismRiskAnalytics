import string
import re
import difflib
import json
from pathlib import Path


VERSION = "0.7.3"
DEBUG_MODE = True

DATABASE_PATH = Path("databases") / VERSION

SUPPORTED_LANGUAGES = ["en", "tl"]

# Behavioral Indicators
#  1. Response To Name
#  2. Eye Contact
#  3. Joint Attention
#  4. Gesture Use
#  5. Social Interaction
#  6. Sharing Interest
#  7. Play Behavior
#  8. Language Communication
#  9. Following Instructions
# 10. Repetitive Behaviors / Routines
# 11. Sensory Responses
# 12. Emotional Response To Change
# 13. Fixated / Restricted Interest
# Note: Q1 to Q5 are only being used at the time.

FEATURES = [
    "response_to_name",
    "eye_contact",
    "joint_attention",
    "gesture_use",
    "social_interaction",
    "sharing_interest",
    "play_behavior",
    "language_communication",
    "following_instructions",
    "repetitive_behaviors_routines",
    "sensory_responses",
    "emotional_response_to_change",
    "fixated_restricted_interest"
]

NEGATION_WORDS = {
    "no","not","don't","never",
    "dont","doesn't","doesnt","isn't",
    "isnt","cannot","can't","cant",
    "won't","wont","without","neither","nor","nothing","nowhere",
    "none","nobody",

    "hindi","wala","di","ayaw"
    }

RESPONSES = {
    "en": {
        "welcome": "Welcome to AuRA.",
        "select_language": "Please select your preferred language.",
        "consent": "Before we begin, please review the consent information.",
        "child_info": "Let's start with some information about your child.",
    },

    "tl": {
        "welcome": "Maligayang pagdating sa AuRA.",
        "select_language": "Pumili ng iyong nais na wika.",
        "consent": "Bago tayo magsimula, pakibasa ang impormasyon tungkol sa pahintulot.",
        "child_info": "Magsimula tayo sa ilang impormasyon tungkol sa iyong anak.",
    }
}



DATABASE_FILE = (
    DATABASE_PATH /
    f"behavioral_indicators_{VERSION}.json"
)

with open(DATABASE_FILE, "r", encoding="utf-8") as file:
    behavioral_indicators = json.load(file)


## Text Preprocessing

def process_text(text, language, target_indicator):
    msg = normalize_text(text)
    tokens = tokenize_text(msg)
    detected = detect_behavioral_indicators(msg, language, target_indicator)
    vector = multi_hot_encode(detected)

    return msg, tokens, detected, vector


def normalize_text(text):
    text = text.lower()
    text = text.replace("'", "")
    text = re.sub(f"[{re.escape(string.punctuation)}]", "", text)
    text = " ".join(text.split())

    return text




## NLP Extraction and Behavioral Indicator Detection

def tokenize_text(text):
    return normalize_text(text).split()

def detect_negation(msg):
    if not msg:
        return False
    return any(word in msg.split() for  word in NEGATION_WORDS)

def is_negated(tokens, index):
    start = max(0, index - 3)

    return any(token in NEGATION_WORDS for token in tokens[start:index])

def token_match_pattern(msg_tokens, pattern, token_cutoff=0.8, threshold=0.67):

    pattern_tokens = tokenize_text(pattern)

    if len(msg_tokens) < len(pattern_tokens):
        return None

    for i in range(len(msg_tokens) - len(pattern_tokens) + 1):

        window = msg_tokens[i:i + len(pattern_tokens)]
        matched = 0

        for msg_token, pattern_token in zip(window, pattern_tokens):

            similarity = difflib.SequenceMatcher(
                None,
                msg_token,
                pattern_token
            ).ratio()

            if similarity >= token_cutoff:
                matched += 1

        score = matched / len(pattern_tokens)

        if score >= threshold:
            return i, i + len(pattern_tokens)

    return None

def search_feature_tokens(tokens, feature_terms, token_cutoff=0.8, threshold=0.67):

    matches = []

    for term in feature_terms:

        pattern_tokens = tokenize_text(term)

        if len(tokens) < len(pattern_tokens):
            continue

        for i in range(len(tokens) - len(pattern_tokens) + 1):
            window = tokens[i:i + len(pattern_tokens)]
            matched = 0

            for msg_token, pattern_token in zip(window, pattern_tokens):

                similarity = difflib.SequenceMatcher(None, msg_token, pattern_token).ratio()
                if similarity >= token_cutoff:
                    matched += 1

            score = matched / len(pattern_tokens)

            if score >= threshold:
                matches.append((term, score))
                break

    return matches


def determine_polarity(tokens, match_start, match_end, base_polarity):

    # start = max(0, match_start - 3)
    # end = min(len(tokens), match_end + 3)

    # context = tokens[start:end]

    preceding_tokens = tokens[max(0, match_start - 3):match_start]

    if any(token in NEGATION_WORDS for token in preceding_tokens):
        if base_polarity == "concern":
            return "neutral"
        if base_polarity == "neutral":
            return "concern"

    return base_polarity

def get_keyword_polarity(tokens, keyword, keyword_type):
    keyword_tokens = tokenize_text(keyword)

    for i in range(len(tokens) - len(keyword_tokens) + 1):
        window = tokens[i:i + len(keyword_tokens)]

        if window == keyword_tokens:

            # start = max(0, i - 3)
            # preceding_tokens = tokens[start:i]

            # if any(token in NEGATION_WORDS for token in preceding_tokens):

            #     if keyword_type == "concern":
            #         return "neutral"
            #     if keyword_type == "neutral":
            #         return "concern"

            return keyword_type
        
    return None


def detect_behavioral_indicators(msg, language, target_indicator):
    detected = {}
    tokens = tokenize_text(msg)

    indicator_data = behavioral_indicators.get(target_indicator)

    if indicator_data is None:
        return detected

    language_data = indicator_data.get(language, {})

    # Neutral-negation matching
    for pattern in language_data.get("neutral_negation_phrases", []):   
        if contains_phrase(msg, pattern):
            print("MATCHED NEUTRAL NEGATION: ", pattern)
            detected[target_indicator] = "neutral"
            return detected

    # Exact concern matching
    for pattern in language_data.get("concern_phrases", []):
        if contains_phrase(msg, pattern):
            detected[target_indicator] = "concern"
            return detected 
    

    # Exact neutral matching
    for pattern in language_data.get("neutral_phrases", []):
        if contains_phrase(msg, pattern):
            detected[target_indicator] = "neutral"
            return detected
    
    # Keyword-based detection
    keyword_result = detect_by_keywords(msg, language_data)

    if keyword_result:
        detected[target_indicator] = keyword_result
        return detected

    # Fuzzy concern matching
    for pattern in language_data.get("concern_phrases", []):
        match = token_match_pattern(tokens, pattern)

        if match:
            start, end = match

            detected[target_indicator] = determine_polarity(tokens, start, end, "concern")
            return detected
    

    # Fuzzy neutral matching
    for pattern in language_data.get("neutral_phrases", []):
            match = token_match_pattern(tokens, pattern)

            if match:
                start, end = match
                detected[target_indicator] = determine_polarity(tokens, start, end, "neutral")
                return detected
            
    return detected

def contains_phrase(msg, phrase):
    return bool(re.search(rf"\b{re.escape(phrase)}\b", msg))


def detect_by_keywords(msg, language_data):

    tokens = tokenize_text(msg)

    concern_keywords = language_data.get("concern_keywords", [])
    neutral_keywords = language_data.get("neutral_keywords", [])
    feature_terms = language_data.get("feature_terms", [])

    # has_feature = any(term in msg for term in feature_terms)
    feature_matches = search_feature_tokens(tokens, feature_terms)

    if not feature_matches:
        return None
    
    # Check concern keywords
    for keyword in concern_keywords:
        result = get_keyword_polarity(tokens, keyword, "concern")

        if result:
            return result

    # Check neutral keywords
    for keyword in neutral_keywords:
        result = get_keyword_polarity(tokens, keyword, "neutral")

        if result:
            return result

    return None

## FEATURE ENCODING

def multi_hot_encode(detected):

    vector = [0] * len(FEATURES)

    detected_indicators = list(detected.keys())
    features = [
            indicator 
            for indicator, polarity in detected.items()
            if indicator in FEATURES and polarity == "concern"
        ]

    for indicator, polarity in detected.items():
        if indicator in FEATURES and polarity == "concern":
            index = FEATURES.index(indicator)
            vector[index] = 1
    
    return vector, detected_indicators, features


QUESTIONS = {
    "en": [
        {
            "id": "Q1",
            "indicator": "response_to_name",
            "question": "Response To Name"
        },
        {
            "id": "Q2",
            "indicator": "eye_contact",
            "question": "Eye Contact"
        },
        {
            "id": "Q3",
            "indicator": "joint_attention",
            "question": "Joint Attention"
        },
        {
            "id": "Q4",
            "indicator": "gesture_use",
            "question": "Gesture Use"
        },
        {
            "id": "Q5",
            "indicator": "social_interaction",
            "question": "Social Interaction"
        }
    ],

    "tl": [
        {
            "id": "Q1",
            "indicator": "response_to_name",
            "question": "Pagtugon sa Pangalan"
        },
        {
            "id": "Q2",
            "indicator": "eye_contact",
            "question": "Pakikipagtitigan"
        },
        {
            "id": "Q3",
            "indicator": "joint_attention",
            "question": "Pinagsasaluhang Atensyon"
        },
        {
            "id": "Q4",
            "indicator": "gesture_use",
            "question": "Paggamit ng mga Kilos"
        },
        {
            "id": "Q5",
            "indicator": "social_interaction",
            "question": "Pakikisalamuha"
        }
    ]
}

def run_questionnaire(session):

    language = session["language"]

    cumulative_vector = [0] * len(FEATURES)
    responses = []

    for question in QUESTIONS[language]:

        print(question["question"])
        main_response = input("> ")

        msg, tokens, detected, vector_data = process_text(
            main_response, 
            language,
            question["indicator"])

        question_vector = vector_data[0]

        cumulative_vector = [
            max(old, new)
            for old, new in zip(
                cumulative_vector,
                question_vector
            )
        ]

        responses.append({
            "question": question["id"],
            "main_response": main_response,
            "detected": detected,
            "question_vector": question_vector
        })

        if DEBUG_MODE:
            print("Detected: ", detected)
            print("Question vector: ", question_vector)
            print("Cumulative: ", cumulative_vector)

    return {
        "responses": responses,
        "cumulative_vector": cumulative_vector
    }

def ml_prediction():
    # dummy
    return

def main():
    language = "tl"

    print("AuRA NLP Debug Mode")
    print("Language:", language)

    result = run_questionnaire({
        "language": language
    })

    final_vector = result["cumulative_vector"]

    if result is None:
        return

    print("\nFinal ML input vector:")
    print(result["cumulative_vector"])

    # prediction = model.predict([final_vector])

    


# ============================================================
# PROGRAM START
# ============================================================

if __name__ == "__main__":
    main()