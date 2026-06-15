import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from dotenv import load_dotenv
import requests

load_dotenv()

class RAGEngine:
    def __init__(self):
        self.index = None
        self.trails_data = None
        self.embedding_model = None
        self.load_components()

    def load_components(self):
        data_dir = os.path.join(os.path.dirname(__file__), '../data')
        embeddings_path = os.path.join(data_dir, 'embeddings.npy')
        mapping_path = os.path.join(data_dir, 'index_mapping.json')
        
        embeddings = np.load(embeddings_path)
        
        with open(mapping_path, 'r', encoding='utf-8') as f:
            paths_mapping = json.load(f)
            
        self.trails_data = []
        for rel_path in paths_mapping:
            full_path = os.path.join(data_dir, rel_path)
            with open(full_path, 'r', encoding='utf-8') as f:
                self.trails_data.append(json.load(f))
            
        dimension = embeddings.shape[1]
        faiss.normalize_L2(embeddings)
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)
        
        self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')

    def get_answer(self, messages, current_state):
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        
        decision_system_prompt = f"""Jesteś systemem do aktualizacji danych z tekstu. Wygeneruj poprawny obiekt JSON i NIC WIĘCEJ.

Oto OBECNY STAN Twojej wiedzy o wymaganiach użytkownika:
{json.dumps(current_state, ensure_ascii=False, indent=2)}

ZASADY:
1. Przeanalizuj NOWĄ wiadomość użytkownika.
2. Jeśli użytkownik podał informacje pasujące do pól, które obecnie mają wartość `null`, ZAKTUALIZUJ JE.
3. Jeśli użytkownik nie podał nowych informacji, po prostu przepisz OBECNY STAN bez zmian.
4. ABSOLUTNIE ZABRONIONE JEST USUWANIE DANYCH! Jeśli jakieś pole miało już wartość, NIE WOLNO Ci zmienić jej z powrotem na null.
5. ZAWSZE zwracaj TYLKO i WYŁĄCZNIE czysty JSON."""

        decision_messages = [
            {"role": "system", "content": decision_system_prompt},
            {"role": "user", "content": f"Nowa wiadomość użytkownika: {last_user_msg}"}
        ]
        
        response = requests.post("http://localhost:11434/api/chat", json={
            "model": "llama3.2",
            "messages": decision_messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0}
        })
        
        if response.status_code != 200:
            return f"Error communicating with local model: {response.text}", current_state
            
        decision_text = response.json()['message']['content']
        
        try:
            state = json.loads(decision_text)
            for k, v in current_state.items():
                if v and str(v).lower() != "null":
                    state[k] = v
        except json.JSONDecodeError:
            state = current_state 
            
        filled_slots = 0
        keywords = []
        for key in ["doswiadczenie", "czas_lub_dystans", "preferencje", "z_kim_idzie"]:
            val = state.get(key)
            if val and str(val).lower() != "null" and len(str(val)) > 2:
                filled_slots += 1
                keywords.append(str(val))
                
        user_msgs = sum(1 for m in messages if m["role"] == "user")
        
        if filled_slots < 3 and user_msgs < 4:
            if not state.get("doswiadczenie") or str(state["doswiadczenie"]).lower() == "null":
                return "Jakie masz doświadczenie w chodzeniu po górach? Jesteś początkujący, czy masz już jakieś za sobą?", state
            if not state.get("czas_lub_dystans") or str(state["czas_lub_dystans"]).lower() == "null":
                return "Ile czasu chcesz przeznaczyć na wycieczkę? Szukasz czegoś na cały dzień, czy krótszego spaceru?", state
            if not state.get("preferencje") or str(state["preferencje"]).lower() == "null":
                return "Masz jakieś konkretne preferencje? Wolisz łagodne doliny, czy może szczyty z ładnymi widokami i ekspozycją?", state
            if not state.get("z_kim_idzie") or str(state["z_kim_idzie"]).lower() == "null":
                return "Z kim wybierasz się na szlak? Idziesz sam, ze znajomymi, czy może z dziećmi?", state
        
        search_query = " ".join(keywords)
        if not search_query.strip():
            search_query = "ciekawy szlak tatry"
            
        query_vector = self.embedding_model.encode([search_query], convert_to_numpy=True)
        faiss.normalize_L2(query_vector)
        distances, indices = self.index.search(query_vector, 3)
        
        retrieved_trails = [self.trails_data[idx] for idx in indices[0]]
        
        context = ""
        for i, trail in enumerate(retrieved_trails):
            context += f"\n--- Szlak {i+1}: {trail['nazwa']} ---\n"
            context += f"{trail['opis'][:800]}\n"
            
        final_system_prompt = f"""Jesteś ekspertem górskim. Poniżej znajduje się historia rozmowy z użytkownikiem oraz kontekst z naszej bazy danych szlaków.
Zaproponuj użytkownikowi szlak WYŁĄCZNIE z podanej BAZY DANYCH, pasujący do jego preferencji. 
Uzasadnij wybór powołując się na informacje techniczne (np. czas, trudność) wyciągnięte z bazy.
NIE zmyślaj szlaków, których nie ma w kontekście!

BAZA DANYCH (KONTEKST):
{context}"""
        
        final_messages = [{"role": "system", "content": final_system_prompt}] + messages
        
        final_response = requests.post("http://localhost:11434/api/chat", json={
            "model": "llama3.2",
            "messages": final_messages,
            "stream": False,
            "options": {"temperature": 0.2}
        })
        
        if final_response.status_code == 200:
            return final_response.json()['message']['content'], state
        else:
            return f"Error during final answer generation: {final_response.text}", state

rag_engine = RAGEngine()
