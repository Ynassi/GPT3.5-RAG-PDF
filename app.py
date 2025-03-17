from flask import Flask, request, jsonify, render_template, send_from_directory
from worker import index_pdf, query_rag, watson_api_key, watson_url
import os
import traceback
import time
from ibm_watson import TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

app = Flask(__name__, static_folder='static')

# Initialisation de Watson TTS
authenticator = IAMAuthenticator(watson_api_key)
text_to_speech = TextToSpeechV1(authenticator=authenticator)
text_to_speech.set_service_url(watson_url)

@app.route("/")
def home():
    return render_template("index.html")

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier envoyé"}), 400

    file = request.files["file"]
    upload_folder = "uploads"
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    filepath = os.path.join(upload_folder, file.filename)
    
    try:
        file.save(filepath)
        response = index_pdf(filepath)
        return jsonify({"message": "Fichier indexé avec succès"}), 200
    except Exception as e:
        return jsonify({"error": f"Erreur lors de l'indexation du fichier: {str(e)}"}), 500

@app.route("/ask", methods=["POST"])
def ask_question():
    data = request.json
    question = data.get("question", "")
    print(f"Question reçue: {question}")

    if not question:
        return jsonify({"error": "Question vide"}), 400

    try:
        # Génération de la réponse
        response_text = query_rag(question)
        print(f"Réponse obtenue : {response_text}")

        # Générer l'audio mais ne pas le jouer automatiquement
        audio_url = synthesize_voice(response_text)  # Retourne un lien vers le fichier audio

        # Retourne la réponse texte et l'URL de l'audio
        return jsonify({"response": response_text, "audio_url": audio_url})
    except Exception as e:
        return jsonify({"error": f"Erreur lors de l'interrogation du modèle : {str(e)}"}), 500

def synthesize_voice(text):
    try:
        # Assurer que le dossier pour l'audio existe
        audio_dir = "static/audio/"
        os.makedirs(audio_dir, exist_ok=True)

        # Générer un nom unique basé sur un timestamp
        timestamp = int(time.time())  # Exemple : 1710512345
        audio_filename = f"output_{timestamp}.wav"
        audio_path = os.path.join(audio_dir, audio_filename)

        # Synthèse vocale avec Watson TTS
        tts_response = text_to_speech.synthesize(
            text, voice="fr-FR_ReneeV3Voice", accept="audio/wav"
        ).get_result().content

        # Enregistrer l'audio
        with open(audio_path, "wb") as f:
            f.write(tts_response)

        # Retourne l'URL relative unique de l'audio
        return f"/static/audio/{audio_filename}"

    except Exception as e:
        print("❌ Erreur synthèse vocale:", str(e))
        return None

@app.route("/cleanup_audio", methods=["POST"])
def cleanup_audio():
    audio_dir = "static/audio/"
    try:
        if os.path.exists(audio_dir):
            now = time.time()
            for file in os.listdir(audio_dir):
                file_path = os.path.join(audio_dir, file)
                if file.endswith(".wav") and os.path.isfile(file_path):
                    file_age = now - os.path.getctime(file_path)
                    if file_age > 600:  # Supprime les fichiers de plus de 10 minutes
                        os.remove(file_path)
        return jsonify({"message": "Fichiers audio nettoyés"}), 200
    except Exception as e:
        return jsonify({"error": f"Erreur nettoyage audio : {str(e)}"}), 500
    
if __name__ == "__main__":
    app.run(debug=True)
