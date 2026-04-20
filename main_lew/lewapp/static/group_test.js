"use strict";

/************************************************************
 *                      UTILS / HELPERS                     *
 ************************************************************/

// Получение CSRF-токена из cookies (необходим для POST-запросов)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

/************************************************************
 *                    DOM ELEMENTS                          *
 ************************************************************/
const groupListContainer = document.getElementById('groupList');
const createGroupButton = document.getElementById('createGroupButton');
const groupNameInput = document.getElementById('groupName');
const groupDescriptionInput = document.getElementById('groupDescription');
const groupUsersInput = document.getElementById('groupUsers');

const activeChatSection = document.getElementById('activeChat');
const activeGroupNameSpan = document.getElementById('activeGroupName');
const activeGroupInfoDiv = document.getElementById('active-group-info');
const chatMessagesContainer = document.getElementById('chat-messages');
const sendGroupMessageButton = document.getElementById('sendGroupMessageButton');
const groupMessageText = document.getElementById('groupMessageText');
const groupFileInput = document.getElementById('groupFileInput');

/************************************************************
 *                 ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ                    *
 ************************************************************/
let currentGroupId = null;          // ID открытой в данный момент группы
let groupSocket = null;             // WebSocket соединение для текущей группы

/************************************************************
 *                    ЗАГРУЗКА ГРУПП                         *
 ************************************************************/
function loadGroups() {
    fetch('/my_groups/')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.json();
        })
        .then(groups => {
            groupListContainer.innerHTML = '';
            groups.forEach(group => {
                const div = document.createElement('div');
                div.className = 'group-item';
                div.textContent = group.name;
                div.dataset.id = group.id;
                div.dataset.name = group.name;
                div.addEventListener('click', () => openGroup(group.id, group.name));
                groupListContainer.appendChild(div);
            });
        })
        .catch(err => {
            console.error('Ошибка загрузки групп:', err);
            groupListContainer.innerHTML = '<p style="color:red;">Не удалось загрузить группы</p>';
        });
}

/************************************************************
 *                   СОЗДАНИЕ ГРУППЫ                         *
 ************************************************************/
createGroupButton.addEventListener('click', function () {
    const name = groupNameInput.value.trim();
    const description = groupDescriptionInput.value.trim();
    const usernames = groupUsersInput.value.split(',').map(s => s.trim()).filter(s => s);

    if (!name || !description) {
        alert('Название и описание группы обязательны');
        return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    usernames.forEach(username => formData.append('user_ids', username));

    fetch('/create_group_chat/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrftoken
        },
        body: formData,
        credentials: 'same-origin'
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => { throw new Error(`HTTP ${response.status}: ${text}`); });
        }
        return response.json();
    })
    .then(data => {
        alert('Группа успешно создана!');
        // Очищаем поля формы
        groupNameInput.value = '';
        groupDescriptionInput.value = '';
        groupUsersInput.value = '';
        // Обновляем список групп
        loadGroups();
    })
    .catch(err => {
        console.error('Ошибка создания группы:', err);
        alert('Не удалось создать группу: ' + err.message);
    });
});

/************************************************************
 *               ОТКРЫТИЕ ГРУППОВОГО ЧАТА                    *
 ************************************************************/
function openGroup(groupId, groupName) {
    // Закрываем предыдущее соединение, если оно было
    if (groupSocket) {
        groupSocket.close();
        groupSocket = null;
    }

    currentGroupId = groupId;
    activeGroupNameSpan.textContent = groupName;
    activeChatSection.style.display = 'block';
    chatMessagesContainer.innerHTML = '';  // очищаем историю
    activeGroupInfoDiv.textContent = 'Подключение...';

    // Формируем WebSocket URL (ws:// или wss://)
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/chat/${groupId}/`;
    groupSocket = new WebSocket(wsUrl);

    groupSocket.onopen = () => {
        console.log(`WebSocket для группы ${groupId} открыт`);
        activeGroupInfoDiv.textContent = 'Подключено ✅';
    };

    groupSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'history') {
            // Загружаем историю сообщений
            const messages = data.messages;
            messages.forEach(msg => addMessageToChat(msg));
        } else if (data.type === 'new_message') {
            // Добавляем новое сообщение
            addMessageToChat(data.message);
        }
    };

    groupSocket.onclose = (event) => {
        console.log(`WebSocket для группы ${groupId} закрыт`, event);
        activeGroupInfoDiv.textContent = 'Соединение закрыто ❌';
        if (!event.wasClean) {
            activeGroupInfoDiv.textContent += ' (нештатно)';
        }
    };

    groupSocket.onerror = (error) => {
        console.error('Ошибка WebSocket:', error);
        activeGroupInfoDiv.textContent = 'Ошибка соединения ⚠️';
    };
}

/************************************************************
 *            ОТОБРАЖЕНИЕ СООБЩЕНИЯ В ЧАТЕ                  *
 ************************************************************/
function addMessageToChat(msg) {
    const container = chatMessagesContainer;
    const div = document.createElement('div');
    div.className = 'message';

    // Формируем HTML для прикреплённых файлов
    let mediaHtml = '';
    if (msg.media && msg.media.length > 0) {
        mediaHtml = '<div class="message-media">📎 ';
        msg.media.forEach((file, index) => {
            // Предполагается, что файл можно скачать по ссылке /download?id=<file.id>
            // В зависимости от реализации бэкенда формат может отличаться
            mediaHtml += `<a href="/download?id=${file.id}" download>${file.name}</a>`;
            if (index < msg.media.length - 1) mediaHtml += ', ';
        });
        mediaHtml += '</div>';
    }

    div.innerHTML = `
        <span class="message-author">${msg.author}:</span>
        <span class="message-text">${msg.text}</span>
        ${mediaHtml}
    `;

    container.appendChild(div);
    container.scrollTop = container.scrollHeight;  // прокрутка вниз
}

/************************************************************
 *               ОТПРАВКА СООБЩЕНИЯ В ГРУППУ                 *
 ************************************************************/
sendGroupMessageButton.addEventListener('click', function () {
    if (!groupSocket || groupSocket.readyState !== WebSocket.OPEN) {
        alert('Нет активного соединения с группой');
        return;
    }

    const text = groupMessageText.value.trim();
    const files = Array.from(groupFileInput.files);

    // Если нет текста и нет файлов — не отправляем
    if (text === '' && files.length === 0) {
        return;
    }

    // Если файлов нет — отправляем сразу
    if (files.length === 0) {
        const messageData = {
            action: 'send_message',
            text: text,
            media: []
        };
        groupSocket.send(JSON.stringify(messageData));
        clearInputs();
        return;
    }

    // Чтение файлов и отправка
    const filesData = [];
    let processedCount = 0;

    function processNextFile(index) {
        if (index >= files.length) {
            // Все файлы прочитаны — отправляем сообщение
            const messageData = {
                action: 'send_message',
                text: text,
                media: filesData
            };
            groupSocket.send(JSON.stringify(messageData));
            clearInputs();
            return;
        }

        const file = files[index];
        const reader = new FileReader();

        reader.onload = (event) => {
            const arrayBuffer = event.target.result;
            const byteArray = new Uint8Array(arrayBuffer);
            // Сохраняем как массив чисел (JSON сериализует его корректно)
            filesData.push({
                filename: file.name,
                data: Array.from(byteArray)  // преобразуем Uint8Array в обычный массив
            });
            processedCount++;
            processNextFile(index + 1);
        };

        reader.onerror = (error) => {
            console.error('Ошибка чтения файла:', file.name, error);
            processedCount++;
            processNextFile(index + 1);
        };

        reader.readAsArrayBuffer(file);
    }

    processNextFile(0);
});

// Вспомогательная функция очистки полей ввода
function clearInputs() {
    groupMessageText.value = '';
    groupFileInput.value = '';
}

/************************************************************
 *                      ИНИЦИАЛИЗАЦИЯ                        *
 ************************************************************/
document.addEventListener('DOMContentLoaded', function () {
    loadGroups();
});