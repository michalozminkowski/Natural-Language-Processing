import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import requests
from config import OLLAMA_EXTRACT_MODEL, OLLAMA_RESPONSE_MODEL, OLLAMA_URL, EMBEDDING_MODEL
from scripts.recommender import rank_trails,format_duration

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

        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    def get_answer(self, messages, current_state):
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        last_assistant_msg = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
        user_message_count = sum(
            1
            for message in messages
            if message.get("role") == "user"
        )

        selected_extraction_model = (
            OLLAMA_RESPONSE_MODEL
            if user_message_count == 1
            else OLLAMA_EXTRACT_MODEL
        )
        print(
            f"[OLLAMA] Analiza wiadomości użytkownika "
            f"nr {user_message_count} przez model: {selected_extraction_model}",
            flush=True
        )
        default_state = {
            "doswiadczenie": None,
            "kondycja": None,
            "czas_lub_dystans": None,
            "poziom_trudnosci": None,
            "ekspozycja": None,
            "z_kim_idzie": None,
            "dzieci": None,
            "preferencje": None,
            "ograniczenia_zdrowotne": None
        }

        if current_state is None:
            current_state = {}

        for key, value in default_state.items():
            current_state.setdefault(key, value)

        decision_system_prompt = f"""
Jesteś modułem NLP do ekstrakcji preferencji użytkownika z rozmowy o trasach górskich.
Twoim zadaniem jest zaktualizować profil użytkownika na podstawie NOWEJ wiadomości.

Zwróć WYŁĄCZNIE poprawny JSON.
Nie dodawaj komentarzy.
Nie używaj markdown.
Nie usuwaj wcześniejszych danych.

OBECNY PROFIL UŻYTKOWNIKA:
{json.dumps(current_state, ensure_ascii=False, indent=2)}

SCHEMAT JSON, który masz zwrócić:
{{
  "doswiadczenie": string | null,
  "kondycja": string | null,
  "czas_lub_dystans": string | null,
  "poziom_trudnosci": string | null,
  "ekspozycja": string | null,
  "z_kim_idzie": string | null,
  "dzieci": boolean | null,
  "preferencje": string | null,
  "ograniczenia_zdrowotne": string | null
}}

ZNACZENIE PÓL:
- doswiadczenie: np. "początkujący", "średniozaawansowany", "doświadczony"
- kondycja: np. "słaba", "średnia", "dobra", "bardzo dobra"
- czas_lub_dystans: np. "3 godziny", "10 km", "cały dzień"
- poziom_trudnosci: np. "łatwa", "średnia", "trudna"
- ekspozycja: informacja czy użytkownik akceptuje przepaście, ekspozycję, trudne fragmenty
- z_kim_idzie: np. "sam", "z dziewczyną", "ze znajomymi", "z rodziną"
- dzieci: true jeśli idzie z dziećmi, false jeśli nie, null jeśli nie wiadomo
- preferencje: np. "widoki", "dolina", "szczyt", "jezioro", "mało ludzi"
- ograniczenia_zdrowotne: np. "problemy z kolanem", "brak", null

PPRZYKŁADY:
Wiadomość: "Jestem początkujący, mam średnią kondycję i chcę łatwą trasę na 3 godziny."
JSON:
{{
  "doswiadczenie": "początkujący",
  "kondycja": "średnia",
  "czas_lub_dystans": "3 godziny",
  "poziom_trudnosci": "łatwa",
  "ekspozycja": null,
  "z_kim_idzie": null,
  "dzieci": null,
  "preferencje": null,
  "ograniczenia_zdrowotne": null
}}

Wiadomość: "Idę z dziewczyną, nie chcemy przepaści, zależy nam na widokach."
JSON:
{{
  "doswiadczenie": null,
  "kondycja": null,
  "czas_lub_dystans": null,
  "poziom_trudnosci": null,
  "ekspozycja": "unika ekspozycji i przepaści",
  "z_kim_idzie": "z dziewczyną",
  "dzieci": false,
  "preferencje": "widoki",
  "ograniczenia_zdrowotne": null
}}

Wiadomość: "Hej mam 21 lat, jestem mężczyzną i chcę wybrać się w góry pierwszy raz."
JSON:
{{
  "doswiadczenie": "początkujący",
  "kondycja": null,
  "czas_lub_dystans": null,
  "poziom_trudnosci": null,
  "ekspozycja": null,
  "z_kim_idzie": null,
  "dzieci": null,
  "preferencje": null,
  "ograniczenia_zdrowotne": null
}}

Wiadomość: "Nigdy nie byłem w górach, ale chciałbym łatwą trasę z widokami."
JSON:
{{
  "doswiadczenie": "początkujący",
  "kondycja": null,
  "czas_lub_dystans": null,
  "poziom_trudnosci": "łatwa",
  "ekspozycja": null,
  "z_kim_idzie": null,
  "dzieci": null,
  "preferencje": "widoki",
  "ograniczenia_zdrowotne": null
}}

WAŻNE:
Jeśli jakaś informacja była już w obecnym profilu, zachowaj ją.
Jeśli nowa wiadomość nie zawiera danego pola, zostaw wcześniejszą wartość.

Frazy typu "pierwszy raz w góry", "pierwszy raz w gory", "pierwszy raz w Tatrach", "nigdy nie byłem w górach", "nigdy nie bylem w gorach", "nie mam doświadczenia", "nie mam doswiadczenia" oznaczają, że użytkownik jest początkujący.

Wiek i płeć użytkownika nie określają trudności trasy. Nie wpisuj wieku ani płci do profilu, chyba że użytkownik poda ograniczenia zdrowotne.

JEŚLI UŻYTKOWNIK PODAJE WIELE INFORMACJI W JEDNEJ WIADOMOŚCI, WYPEŁNIJ WSZYSTKIE ODPOWIEDNIE POLA.
Możesz wnioskować z kontekstu (np. "długie i wymagające trasy" -> czas_lub_dystans: "długa", poziom_trudnosci: "trudna", "chodzę regularnie" -> doswiadczenie: "doświadczony").
"""

        decision_messages = [
            {"role": "system", "content": decision_system_prompt},
            {"role": "user", "content": f"OSTATNIE PYTANIE ASYSTENTA: {last_assistant_msg}\n\nNOWA WIADOMOŚĆ UŻYTKOWNIKA: {last_user_msg}"}
        ]


        response = requests.post(OLLAMA_URL, json={
            "model": selected_extraction_model,
            "messages": decision_messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0}
        })


        if response.status_code != 200:
            return f"Error communicating with local model: {response.text}", current_state

        decision_text = response.json()["message"]["content"]

        try:
            extracted = json.loads(decision_text)
        except json.JSONDecodeError:
            extracted = {}

        state = current_state.copy()

        for key in default_state.keys():
            new_value = extracted.get(key)

            if new_value not in [None, "", "null", [], {}]:
                if isinstance(new_value, list):
                    new_value = ", ".join(map(str, new_value))
                state[key] = new_value

        def is_empty(value):
            return value is None or value == "" or str(value).lower() == "null" or value == [] or value == {}

        required_questions = [
            (
                "doswiadczenie",
                "Jakie masz doświadczenie w chodzeniu po górach? Jesteś początkujący, średniozaawansowany czy doświadczony?"
            ),
            (
                "kondycja",
                "Jak oceniasz swoją kondycję: słaba, średnia, dobra czy bardzo dobra?"
            ),
            (
                "czas_lub_dystans",
                "Ile czasu albo jaki dystans chcesz maksymalnie przeznaczyć na trasę?"
            ),
            (
                "poziom_trudnosci",
                "Jaką trudność trasy preferujesz: łatwą, średnią czy trudną?"
            ),
            (
                "ekspozycja",
                "Czy akceptujesz ekspozycję, przepaście i trudniejsze techniczne fragmenty, czy chcesz ich unikać?"
            ),
            (
                "z_kim_idzie",
                "Z kim idziesz na trasę: sam, z drugą osobą, ze znajomymi, z rodziną czy z dziećmi?"
            ),
            (
                "preferencje",
                "Co jest dla Ciebie najważniejsze na trasie: widoki, dolina, szczyt, jezioro, mało ludzi czy coś innego?"
            )
        ]

        for field, question in required_questions:
            if is_empty(state.get(field)):
                return question, state

        keywords = []
        for value in state.values():
            if value not in [None, "", "null", [], {}]:
                keywords.append(str(value))

        search_query = " ".join(keywords)

        if not search_query.strip():
            search_query = "łatwy szlak Tatry dla początkujących"

        query_vector = self.embedding_model.encode([search_query], convert_to_numpy=True)
        faiss.normalize_L2(query_vector)

        distances, indices = self.index.search(query_vector, 20)

        retrieved_trails = [
            self.trails_data[idx]
            for idx in indices[0]
            if idx >= 0
               and idx < len(self.trails_data)
               and isinstance(self.trails_data[idx], dict)
        ]

        ranked_trails = rank_trails(state, retrieved_trails)

        top_ranked = [
            item for item in ranked_trails
            if not item.get("disqualified", False)
        ][:3]

        if not top_ranked:
            top_ranked = ranked_trails[:3]

        context = ""

        for i, item in enumerate(top_ranked):
            trail = item["trail"]
            score = item["score"]
            reasons = item["reasons"]
            warnings = item["warnings"]

            trail_name = trail.get("name") or trail.get("nazwa") or "Nieznany szlak"
            trail_description = trail.get("description") or trail.get("opis") or ""

            context += f"\n--- Kandydat {i + 1}: {trail_name} ---\n"
            context += f"Score dopasowania: {score}\n"

            context += "Powody dopasowania:\n"
            for reason in reasons:
                context += f"- {reason}\n"

            context += "Ostrzeżenia:\n"
            for warning in warnings:
                context += f"- {warning}\n"

            context += f"Nazwa: {trail_name}\n"
            context += f"Region: {trail.get('region')}\n"
            context += f"Czas przejścia: {format_duration(trail.get('duration_hours'))}\n"
            context += f"Dystans: {trail.get('distance_km')} km\n"
            context += f"Przewyższenie: {trail.get('elevation_gain_m')} m\n"
            context += f"Trudność: {trail.get('difficulty')}/5\n"
            context += f"Trudność techniczna: {trail.get('technical_difficulty')}/5\n"
            context += f"Trudność kondycyjna: {trail.get('fitness_difficulty')}/5\n"
            context += f"Ekspozycja: {trail.get('exposure')}/5\n"
            context += f"Dla początkujących: {trail.get('suitable_for_beginners')}\n"
            context += f"Dla dzieci: {trail.get('suitable_for_children')}\n"
            context += f"Atrakcje: {', '.join(trail.get('main_attractions', []))}\n"
            context += f"Ryzyka: {', '.join(trail.get('risks', []))}\n"
            context += f"Krótki opis: {trail.get('short_summary')}\n"
            context += f"Opis skrócony: {trail_description[:350]}\n"

        final_system_prompt = f"""
        Jesteś ekspertem górskim i doradcą tras w Tatrach.

        Masz profil użytkownika:
        {json.dumps(state, ensure_ascii=False, indent=2)}

        Poniżej masz kandydatów już posortowanych przez algorytm scoringowy.
        Najwyższy score oznacza najlepsze dopasowanie.

        KANDYDACI:
        {context}

        Zadanie:
1. Wybierz najlepszą trasę z kandydatów.
2. Nie ignoruj ostrzeżeń.
3. Jeśli kandydat ma ostrzeżenie zaczynające się od "DYSKWALIFIKACJA", NIE WOLNO go polecić jako najlepszej propozycji.
4. Użytkownik, który unika przepaści, nie powinien dostać trasy z łańcuchami, żlebem, ekspozycją ani ubezpieczeniami.
5. Nie zmyślaj tras spoza kandydatów.
6. Odpowiedz po polsku, konkretnie i praktycznie.
7. Nie kopiuj całych fragmentów artykułu źródłowego.
8. Odpowiedź ma mieć maksymalnie 180 słów.
9. Jeżeli żadna trasa nie spełnia wszystkich wymagań, zaproponuj najbezpieczniejszy kompromis i jasno napisz, które wymaganie nie jest spełnione.
10. Jeśli kandydat ma ostrzeżenie "NIE SPEŁNIA PREFERENCJI", nie pisz, że spełnia tę preferencję.
11. Nie przedstawiaj trasy jako widokowej, jeśli ostrzeżenia mówią, że nie jest szczególnie widokowa.
12. Alternatywa także musi być zgodna z wymaganiami bezpieczeństwa użytkownika.
13. Pisz w normalnym formnie, nie uzywaj pogrubień typu (**XXX**) itp. ma być czysty tekst.

Jeśli użytkownik unika przepaści, każde wystąpienie łańcuchów, żlebu, ekspozycji lub ubezpieczeń traktuj jako poważny problem, a nie neutralną informację.

        Format odpowiedzi:
        Najlepsza propozycja:
        Dlaczego pasuje:
        Na co uważać:
        Alternatywa:
        """

        final_messages = [
                             {"role": "system", "content": final_system_prompt}
                         ] + messages
        print(
            f"[OLLAMA] Generowanie końcowej rekomendacji przez model: "
            f"{OLLAMA_RESPONSE_MODEL}",
            flush=True
        )
        final_response = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_RESPONSE_MODEL,
            "messages": final_messages,
            "stream": False,
            "options": {"temperature": 0.2}
        })

        if final_response.status_code == 200:
            answer = final_response.json()["message"]["content"]

            answer = answer.replace("**", "")

            return answer, state

        return f"Error during final answer generation: {final_response.text}", state
rag_engine = RAGEngine()
