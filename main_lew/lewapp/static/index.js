"use strict"

let usernameInputForMessage = document.getElementById("usernameInputForMessage");
let textInputForMessage = document.getElementById("textInputForMessage");
let fileInputForMessage = document.getElementById("fileInputForMessage");
let sendMessageButton = document.getElementById("sendMessageButton");

let usernameInputForCall = document.getElementById("usernameInputForCall");
let makeCallButton = document.getElementById("makeCallButton");

let callsSec = document.getElementById("callRequests");
let messegesSec = document.getElementById("messeges");

let callsSocket = new WebSocket("ws://127.0.0.1:8000/ws/call/");
let messagesSocket = new WebSocket("ws://127.0.0.1:8000/ws/chat/");

let mediaRecorder;
let isStarting = false;

const audio = new Audio();
const mediaSource = new MediaSource();

let sourceBuffer = null;
let queue = [];

audio.src = URL.createObjectURL(mediaSource);

mediaSource.onsourceopen = () => {
    sourceBuffer = mediaSource.addSourceBuffer("audio/webm; codecs=opus");

    sourceBuffer.onupdateend = () => {
        if (queue.length > 0 && !sourceBuffer.updating)
            sourceBuffer.appendBuffer(queue.shift());
    };
};

async function startRecording(activeCall) {
    if (isStarting || (mediaRecorder && mediaRecorder.state != "inactive"))
        return;

    isStarting = true;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            const reader = new FileReader();

            reader.onloadend = () => {
                const base64Chunk = reader.result.split(",")[1];
                const data = {
                    "action": "sendAudio",
                    "username": activeCall,
                    "chunk": base64Chunk
                };

                callsSocket.send(JSON.stringify(data));
            };

            reader.readAsDataURL(event.data);
        }
    };

    mediaRecorder.onstop = () => {
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorder.start(100);

    isStarting = false;
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state != "inactive")
        mediaRecorder.stop();
}

callsSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.audio) {
        const byteString = atob(data.audio);

        let byteNumbers = [];

        for (let i = 0; i < byteString.length; i++)
            byteNumbers.push(byteString.charCodeAt(i));

        const byteArray = new Uint8Array(byteNumbers);

        if (sourceBuffer && !sourceBuffer.updating) {
            sourceBuffer.appendBuffer(byteArray);

            if (audio.paused)
                audio.play();
        }
        else
            queue.push(byteArray);

        return;
    }

    const calls = JSON.parse(data.calls);

    let html = "", activeCall = null;

    for (let i = 0; i < calls.length; i++) {
        const call = calls[i];

        if (call["accepted"]) {
            activeCall = call["user"];
            html += `<p>Активный звонок: ${call["user"]}</p><button class="declineCallButton" callId=${call["id"]}>Завершить</button>`;
        }

        else if (call["accepted"] == null) {
            if (activeCall == call["user"])
                activeCall = null;

            html += `<p>Входящий звонок: ${call["user"]}</p><button class="acceptCallButton" callId=${call["id"]}>Принять</button><button class="declineCallButton" callId=${call["id"]}>Отклонить</button>`;
        }
    }

    if (activeCall != null)
        startRecording(activeCall);
    else
        stopRecording();

    callsSec.innerHTML = html;

    let acceptCallButtons = document.querySelectorAll(".acceptCallButton");
    let declineCallButtons = document.querySelectorAll(".declineCallButton");

    acceptCallButtons.forEach((button) => {
        const callId = button.getAttribute("callId");

        button.addEventListener("click", () => {
            const data = {
                "action": "callResponse",
                "callId": callId,
                "accepted": true
            }

            callsSocket.send(JSON.stringify(data));
        });
    });

    declineCallButtons.forEach((button) => {
        const callId = button.getAttribute("callId");

        button.addEventListener("click", () => {
            const data = {
                "action": "callResponse",
                "callId": callId,
                "accepted": false
            }

            callsSocket.send(JSON.stringify(data));
        });
    });
};

makeCallButton.addEventListener("click", () => {
    const data = {
        "action": "makeCall",
        "username": usernameInputForCall.value
    };

    callsSocket.send(JSON.stringify(data));

    usernameInputForCall.value = "";
});

messagesSocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const messages = JSON.parse(data.messages);

    let html = "";

    for (let i = 0; i < messages.length; i++) {
        html += `<section><p>${messages[i]["author"]}: ${messages[i]["text"]}</p>`;

        for (let j = 0; j < messages[i]["mediafiles"].length; j++) {
            const mediafile = messages[i]["mediafiles"][j];
            html += `<p><a href="download?id=${mediafile["id"]}" download>Скачать файл ${mediafile["name"]}</a></p>`;
        }

        html += `</section>`;
    }

    messegesSec.innerHTML = html;
};

sendMessageButton.addEventListener("click", () => {
    const files = fileInputForMessage.files;
    
    let data = {};
    let filesData = [];

    if (files.length != 0) {
        const reader = new FileReader();
        let currFileIndex = 0;

        reader.onload = (event) => {
            const arrayBuffer = event.target.result;
            const byteArray = new Uint8Array(arrayBuffer);

            filesData.push({"filename": reader.filename, "data": byteArray});
        };

        reader.onloadend = () => {
            if (filesData.length == files.length) {
                data = {
                    "username": usernameInputForMessage.value,
                    "text": textInputForMessage.value,
                    "media": filesData
                };

                messagesSocket.send(JSON.stringify(data));

                textInputForMessage.value = "";
                fileInputForMessage.value = "";
            }

            else {
                currFileIndex++;

                let file = files[currFileIndex];

                reader.filename = file.name;
                reader.readAsArrayBuffer(file);
            }
        }

        const startFile = files[currFileIndex];

        reader.filename = startFile.name;
        reader.readAsArrayBuffer(startFile);
    }

    else {
        data = {
            "username": usernameInputForMessage.value,
            "text": textInputForMessage.value,
            "media": []
        };

        messagesSocket.send(JSON.stringify(data));

        textInputForMessage.value = "";
        fileInputForMessage.value = "";
    }
});
