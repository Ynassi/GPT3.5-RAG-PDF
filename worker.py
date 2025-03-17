import openai
import PyPDF2
import os
import faiss
import numpy as np
from dotenv import load_dotenv
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# Charger la clé API depuis .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
watson_api_key = os.getenv("WATSONTTS_API_KEY")
watson_url = os.getenv("WATSONTTS_API_URL")

authenticator = IAMAuthenticator(watson_api_key)
text_to_speech = TextToSpeechV1(authenticator=authenticator)
text_to_speech.set_service_url(watson_url)

# Initialisation d'un index FAISS pour stocker les embeddings
dimension = 1536  # Taille de l'embedding OpenAI (pour "text-embedding-ada-002")
index = faiss.IndexFlatL2(dimension)
documents = []  # Stocke les textes associés aux embeddings

try:
    voices = text_to_speech.list_voices().get_result()
    print("✅ Connexion Watson TTS réussie, voix disponibles :", [v["name"] for v in voices["voices"]])
except Exception as e:
    print("❌ Erreur de connexion à Watson TTS :", str(e))

def index_pdf(file_path):
    global index, documents
    # Réinitialiser l'index FAISS et la liste des documents
    index = faiss.IndexFlatL2(dimension)
    documents = []
    
    try:
        with open(file_path, "rb") as f:
            pdf = f.read()  # Lire le fichier PDF
        
        text = extract_text_from_pdf(file_path)
        print(f"Texte extrait du PDF : {text[:500]}...")  # Afficher un aperçu du texte extrait
        
        chunks = split_text(text)
        embeddings = []

        for chunk in chunks:
            embedding = generate_embedding(chunk)
            embeddings.append(embedding)
            print(f"Embedding pour le chunk: {embedding[:5]}")

        embeddings = np.array(embeddings)
        print(f"Embeddings générés, taille : {embeddings.shape}")

        # Indexer les embeddings dans FAISS
        index.add(embeddings)
        print("Embeddings indexés dans FAISS")

        # Ajouter les textes au tableau de documents
        documents.extend(chunks)
        print(f"Documents ajoutés, nombre total de documents : {len(documents)}")

        return {"message": "Fichier indexé avec succès"}
    
    except Exception as e:
        print(f"Erreur lors de l'indexation du PDF : {str(e)}")
        return {"error": f"Erreur lors de l'indexation du fichier : {str(e)}"}


def extract_text_from_pdf(pdf_path):
    """Extrait le texte brut d'un fichier PDF."""
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text.strip()


def split_text(text, chunk_size=500):
    """Divise le texte en segments de taille maximale `chunk_size` caractères."""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


def generate_embedding(chunk):
    text = chunk  # Assurez-vous que `chunk` contient le texte à transformer en embedding

    try:
        # Appel à l'API pour générer l'embedding
        response = openai.Embedding.create(
            input=text,
            model="text-embedding-ada-002"
        )

        # Vérifier que la réponse contient bien des données
        if 'data' in response and len(response['data']) > 0:
            # Accéder à l'embedding de la première entrée dans 'data'
            embedding = response['data'][0]['embedding']
            # Retourner l'embedding sous forme de tableau numpy
            return np.array(embedding)
        else:
            print("Pas de données d'embedding disponibles.")
            raise ValueError("La réponse de l'API ne contient pas d'embeddings valides.")

    except Exception as e:
        print(f"Erreur lors de la génération de l'embedding : {e}")
        raise


def query_rag(question):
    """Effectue une recherche dans l'index FAISS et génère une réponse avec GPT-3.5."""
    question_embedding = generate_embedding(question)  # Générer l'embedding pour la question

    # Rechercher dans l'index FAISS les 3 meilleurs résultats les plus proches
    distances, indices = index.search(np.array([question_embedding]), k=3)

    # Extraire les textes correspondants aux indices retournés
    relevant_texts = [documents[i] for i in indices[0] if i < len(documents)]
    
    # Créer un contexte avec les extraits pertinents
    context = "\n\n".join(relevant_texts)

    # Préparer le prompt pour GPT
    prompt = f"Voici des extraits d'un document PDF :\n{context}\n\nQuestion : {question}\nRéponse :"

    try:
        # Interroger GPT-3.5 pour générer une réponse avec l'endpoint correct pour un modèle de chat
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Utilisation de gpt-3.5-turbo (moins coûteux en tokens)
            messages=[
                {"role": "system", "content": "Tu es un assistant intelligent qui répond en fonction d'un document donné."},
                {"role": "user", "content": prompt}
            ]
        )
        return response['choices'][0]['message']['content']

    except Exception as e:
        print(f"Erreur lors de l'interrogation du modèle : {e}")
        return "Erreur lors de l'interrogation du modèle."


