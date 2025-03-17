function addMessageToHistory(sender, message, senderType) {
    const historyDiv = document.getElementById("conversation-history");
    const messageContainer = document.createElement("div");

    // Déterminer l'image associée
    const avatarSrc = senderType === "user-message" ? "static/img/6492709.png" : "static/img/6492708.png";

    // Ajouter les classes CSS pour le style
    messageContainer.classList.add("message-container", senderType);

    // Structure du message sans attendre l'audio
    messageContainer.innerHTML = `
        ${senderType === "bot-message" ? `<img src="${avatarSrc}" class="message-avatar">` : ""}
        <div class="message-text"><strong>${sender} :</strong> ${message}</div>
        ${senderType === "user-message" ? `<img src="${avatarSrc}" class="message-avatar">` : ""}
    `;

    historyDiv.appendChild(messageContainer);
    historyDiv.scrollTop = historyDiv.scrollHeight;

    return messageContainer; // Retourne l'élément du message pour ajout de l'icône plus tard
}

// Gestion de l'upload du PDF
document.getElementById("uploadForm").addEventListener("submit", function(event) {
    event.preventDefault();
    let formData = new FormData();
    formData.append("file", document.getElementById("file").files[0]);

    fetch("/upload", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            document.getElementById("uploadMessage").textContent = data.message;
            // Masquer la section d'upload et afficher la section de chat
            document.getElementById("upload-section").style.display = "none";
            document.getElementById("chat-section").style.display = "flex";
            addMessageToHistory("Système", "Fichier indexé. Vous pouvez maintenant poser vos questions.", "bot-message");
        } else {
            document.getElementById("uploadMessage").textContent = "Erreur lors du téléchargement du fichier.";
        }
    })
    .catch(error => {
        document.getElementById("uploadMessage").textContent = "Erreur de connexion.";
        console.error(error);
    });
});

// Gestion de l'envoi des messages
document.getElementById("sendButton").addEventListener("click", sendMessage);
document.getElementById("messageInput").addEventListener("keyup", function(event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});
function sendMessage() {
    const messageInput = document.getElementById("messageInput");
    const question = messageInput.value.trim();
    if (!question) return;

    // Afficher immédiatement le message de l'utilisateur
    addMessageToHistory("Vous", question, "user-message");
    messageInput.value = "";

    // Ajouter un message vide avec animation pour le bot
    const botMessageElement = addLoadingMessage("bot-message");

    // Envoyer la question à la route /ask
    fetch("/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ "question": question })
    })
    .then(response => response.json())
    .then(data => {
        if (data.response) {
            // Remplace l'animation par le texte
            updateMessageWithResponse(botMessageElement, data.response);

            // Ajouter l'icône audio quand l'audio est prêt
            if (data.audio_url) {
                loadAudioButton(botMessageElement, data.audio_url);
            }
        } else {
            updateMessageWithResponse(botMessageElement, "Aucune réponse disponible.");
        }
    })
    .catch(error => {
        updateMessageWithResponse(botMessageElement, "Erreur lors de la requête.");
        console.error(error);
    });
}
function addAudioButtonToLastMessage(audioUrl) {
    const historyDiv = document.getElementById("conversation-history");
    const lastMessage = historyDiv.lastElementChild; // Dernier message ajouté

    if (lastMessage && lastMessage.classList.contains("bot-message")) {
        // Création du bouton audio
        const audioButton = document.createElement("button");
        audioButton.classList.add("audio-button");
        audioButton.innerHTML = `<img src="static/img/6492710.png" class="audio-icon">`; // Icône speaker

        // Gestion du clic sur le bouton audio
        audioButton.addEventListener("click", function () {
            if (currentAudio && !currentAudio.paused) {
                // Si un audio est déjà en cours, on l'arrête
                currentAudio.pause();
                currentAudio.currentTime = 0; // Remet à zéro
                currentAudio = null;
            } else {
                // Sinon, on joue le nouvel audio
                currentAudio = new Audio(audioUrl);
                currentAudio.play();

                // Quand l’audio se termine, on remet currentAudio à null
                currentAudio.onended = function () {
                    currentAudio = null;
                };
            }
        });

        // Ajout du bouton à la fin du message du bot
        lastMessage.appendChild(audioButton);
    }
}
let currentAudio = null;

function loadAudioButton(messageElement, audioUrl) {
    // Création du bouton speaker
    const audioButton = document.createElement("button");
    audioButton.classList.add("audio-button");
    audioButton.style.display = "none"; // Caché au départ
    audioButton.innerHTML = `<img src="static/img/6492710.png" class="audio-icon">`;

    // Création de l'audio unique pour CE message
    const audio = new Audio(audioUrl);
    
    // Une fois l'audio prêt, on affiche le bouton
    audio.oncanplaythrough = function () {
        audioButton.style.display = "inline-block";
    };

    // Gestion du clic pour lecture / arrêt
    audioButton.addEventListener("click", function () {
        if (currentAudio && currentAudio !== audio) {
            currentAudio.pause();  // Arrête l'audio en cours
            currentAudio.currentTime = 0;
        }

        if (audio.paused) {
            audio.play();
            currentAudio = audio;  // Met à jour l'audio actif
        } else {
            audio.pause();
            audio.currentTime = 0;
            currentAudio = null;
        }
    });

    // Ajouter le bouton à la fin du message
    messageElement.appendChild(audioButton);
}

function addLoadingMessage(senderType) {
    const historyDiv = document.getElementById("conversation-history");
    const messageContainer = document.createElement("div");

    messageContainer.classList.add("message-container", senderType);

    // Déterminer l'icône (le bot doit avoir son icône)
    const avatarSrc = senderType === "bot-message" ? "static/img/6492708.png" : "";

    // Ajout de l'icône + l'animation
    messageContainer.innerHTML = `
        ${senderType === "bot-message" ? `<img src="${avatarSrc}" class="message-avatar">` : ""}
        <div class="loading-animation">
            <div></div><div></div><div></div><div></div><div></div>
        </div>
    `;

    historyDiv.appendChild(messageContainer);
    historyDiv.scrollTop = historyDiv.scrollHeight;

    return messageContainer; // Retourne l'élément pour mise à jour plus tard
}

function updateMessageWithResponse(messageElement, responseText) {
    // Icône du bot
    const avatarSrc = "static/img/6492708.png";

    // Remplace l'animation par le texte
    messageElement.innerHTML = `
        <img src="${avatarSrc}" class="message-avatar">
        <div class="message-text"><strong>Bot :</strong> ${responseText}</div>
    `;
}
setInterval(() => {
    fetch("/cleanup_audio", { method: "POST" })
        .then(response => response.json())
        .then(data => console.log(data.message || data.error))
        .catch(error => console.error("Erreur nettoyage audio:", error));
}, 300000);  // 5 minutes
