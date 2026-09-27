import json
import boto3
import re
from database import collection
import traceback

print("[INFO] rag_pipeline.py initialized")

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
DISTANCE_THRESHOLD = 2  
MAX_CONTEXT_CHUNKS = 5

# --- YOUR GUARDRAIL CONFIGURATION ---
GUARDRAIL_ID = "kdq0vvtagthv"
GUARDRAIL_VERSION = "2"  

SMALL_TALK_TRIGGERS = {
    "greet":  ["hi", "hello", "hey", "good morning", "good afternoon", "good evening", "howdy"],
    "thanks": ["thanks", "thank you", "thank u", "thx", "ty"],
    "bye":    ["bye", "goodbye", "see you", "see ya", "take care"],
    "ok":     ["ok", "okay", "alright", "got it", "noted"],
    "help":   ["help", "what can you do", "what do you know", "how can you help"],
}

SMALL_TALK_RESPONSES = {
    "greet":  "Hello! How can I help you with Telangana government services today?",
    "thanks": "You're welcome! Feel free to ask if you need anything else.",
    "bye":    "Goodbye! Have a great day.",
    "ok":     "Sure! Let me know if you have any questions.",
    "help":   "I can help you with information about Telangana government services such as Income certificates, Birth certificates, and MeeSeva services. Just ask your question!",
}

def _match_small_talk(text: str):
    cleaned = text.lower().strip().rstrip("!?.,'\"")
    for category, triggers in SMALL_TALK_TRIGGERS.items():
        for trigger in triggers:
            if cleaned == trigger or cleaned.startswith(trigger):
                return SMALL_TALK_RESPONSES[category]
    return None

def get_embedding(text: str):
    try:
        response = bedrock.invoke_model(
            modelId="amazon.titan-embed-text-v2:0",
            body=json.dumps({"inputText": text})
        )
        return json.loads(response["body"].read())["embedding"]
    except Exception as e:
        print(f"[ERROR] Embedding failed: {e}")
        raise

def generate_answer(context: str, question: str, previous_question: str = None) -> tuple:
    prompt = f"""
You are Telangana Seva AI. Answer ONLY using the provided context.

Rules:
1. Do not use outside knowledge.
2. Do not hallucinate.
3. Format the response clearly using Markdown formatting (bolding, bullet points).
4. At the very end of your response, generate exactly 3 relevant follow-up questions the user might logically ask next based on this topic. Format them strictly like this:
---FOLLOW_UPS---
1. [Question 1]
2. [Question 2]
3. [Question 3]

Context:
{context}

Previous Question from User (for conversational context):
{previous_question if previous_question else "None"}

Current Question:
{question}

Answer:
"""
    try:
        # Upgraded to the Converse API for native Guardrail support
        response = bedrock.converse(
            modelId="amazon.nova-lite-v1:0",
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": 700, "temperature": 0.1, "topP": 0.9},
            guardrailConfig={
                "guardrailIdentifier": GUARDRAIL_ID,
                "guardrailVersion": GUARDRAIL_VERSION,
                "trace": "enabled"  # Fixed ValidationException: must be lowercase "enabled" or "disabled"
            }
        )

        # 🛡️ THE GUARDRAIL CHECK
        if response.get('stopReason') == 'guardrail_intervened':
            print("[SECURITY] Guardrail blocked a violative prompt or response.")
            return "I am sorry, but I can only assist with official Telangana government services. I cannot process inappropriate, off-topic, or sensitive requests.", []

        # Parse the safe response
        raw_answer = response["output"]["message"]["content"][0]["text"].strip()

        parts = raw_answer.split("---FOLLOW_UPS---")
        main_answer = parts[0].strip()
        
        follow_ups = []
        if len(parts) > 1:
            lines = parts[1].strip().split('\n')
            for line in lines:
                clean_line = re.sub(r'^[\d\-\.\*]+\s*', '', line).strip()
                if clean_line:
                    follow_ups.append(clean_line)

        return main_answer, follow_ups

    except Exception as e:
        traceback.print_exc()
        return f"LLM Error: {str(e)}", []

def query_chatbot(question: str, enhanced_question: str = None, previous_question: str = None) -> dict:
    small_talk_response = _match_small_talk(question)
    if small_talk_response:
        return {"answer": small_talk_response, "follow_ups": [], "sources": [], "context": []}

    search_query = enhanced_question if enhanced_question else question

    try:
        question_embedding = get_embedding(search_query)
    except Exception:
        return {"answer": "I'm sorry, I encountered a connection error. Please try again.", "follow_ups": [], "sources": [], "context": []}

    try:
        results = collection.query(query_embeddings=[question_embedding], n_results=25)
    except Exception as e:
        return {"answer": "I'm sorry, I encountered a database error. Please try again.", "follow_ups": [], "sources": [], "context": []}

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    filtered = [(doc, meta, dist) for doc, meta, dist in zip(documents, metadatas, distances) if dist <= DISTANCE_THRESHOLD]

    if not filtered:
        return {"answer": "I could not find official information regarding your query in the Telangana government records. Please visit your nearest MeeSeva center or the official state government portal for further assistance.", "follow_ups": [], "sources": [], "context": []}

    unique_docs = []
    seen_sources = set()

    for doc, meta, dist in filtered:
        source = meta.get("source", "unknown")
        if source not in seen_sources:
            unique_docs.append(doc)
            seen_sources.add(source)
        if len(unique_docs) >= MAX_CONTEXT_CHUNKS:
            break

    unique_sources = list(seen_sources)
    context = "\n\n".join(unique_docs)
    
    answer, follow_ups = generate_answer(context, question, previous_question)

    return {
        "answer": answer,
        "follow_ups": follow_ups,
        "sources": unique_sources,
        "context": unique_docs
    }