from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Chatbot
from app.db.chatbot_settings import ChatbotSettings


router = APIRouter(
    prefix="/widget",
    tags=["Widget"],
)


@router.get("/{embed_token}.js")
async def widget_script(
    embed_token: str,
    db: Session = Depends(get_db),
):
    """
    Generate the KNOWA AI chatbot widget dynamically.

    The widget:
    - Loads chatbot configuration from the database
    - Uses custom logo/avatar
    - Uses custom colors
    - Uses custom welcome message
    - Uses custom placeholder
    - Sends messages to /api/v1/widget/chat
    - Maintains conversation history during the page session
    - Supports basic Markdown rendering
    """

    # ============================================================
    # FIND CHATBOT
    # ============================================================

    chatbot = (
        db.query(Chatbot)
        .filter(
            Chatbot.embed_token == embed_token
        )
        .first()
    )

    if chatbot is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid embed token",
        )

    # ============================================================
    # FIND SETTINGS
    # ============================================================

    settings = (
        db.query(ChatbotSettings)
        .filter(
            ChatbotSettings.chatbot_id == chatbot.id
        )
        .first()
    )

    if settings is None:
        raise HTTPException(
            status_code=404,
            detail="Settings not found",
        )

    # ============================================================
    # DATABASE VALUES
    # ============================================================

    chatbot_name = chatbot.name or "KNOWA AI"

    welcome_message = (
        settings.welcome_message
        or "Hi! How can I help you today?"
    )

    placeholder = (
        settings.placeholder
        or "Ask me anything..."
    )

    primary_color = (
        settings.primary_color
        or "#2563eb"
    )

    secondary_color = (
        settings.secondary_color
        or "#ffffff"
    )

    widget_width = (
        settings.widget_width
        or "380px"
    )

    widget_height = (
        settings.widget_height
        or "600px"
    )

    border_radius = (
        settings.border_radius
        or "16px"
    )

    position = (
        settings.position
        or "bottom-right"
    )

    # ============================================================
    # LOGO
    # ============================================================
    #
    # Priority:
    #
    # 1. Custom logo_url
    # 2. avatar_url
    # 3. Default KNOWA logo
    #

    logo_url = (
        settings.logo_url
        or settings.avatar_url
        or "/static/knowa-logo.jpg"
    )

    # ============================================================
    # SAFELY CREATE JAVASCRIPT STRINGS
    # ============================================================

    import json

    js_embed_token = json.dumps(
        chatbot.embed_token
    )

    js_chatbot_name = json.dumps(
        chatbot_name
    )

    js_welcome_message = json.dumps(
        welcome_message
    )

    js_placeholder = json.dumps(
        placeholder
    )

    js_logo_url = json.dumps(
        logo_url
    )

    # ============================================================
    # JAVASCRIPT TEMPLATE
    #
    # IMPORTANT:
    #
    # This is NOT an f-string.
    #
    # Dynamic values are inserted later using .replace().
    #
    # This prevents:
    #
    # SyntaxError: f-string: single '}' is not allowed
    # ============================================================

    js = r"""
(function () {

    "use strict";


    // ============================================================
    // CONFIGURATION
    // ============================================================

    const EMBED_TOKEN = __EMBED_TOKEN__;

    const CHATBOT_NAME = __CHATBOT_NAME__;

    const WELCOME_MESSAGE = __WELCOME_MESSAGE__;

    const PLACEHOLDER = __PLACEHOLDER__;

    const CONFIGURED_LOGO_URL = __LOGO_URL__;


    // ============================================================
    // API BASE
    // ============================================================

    let API_BASE =
        "http://localhost:8000/api/v1";

    let STATIC_BASE =
        "http://localhost:8000/static";


    // ============================================================
    // DETERMINE SCRIPT URL
    // ============================================================

    const currentScript =
        document.currentScript;


    const SCRIPT_URL =
        currentScript
            ? currentScript.src
            : "";


    if (SCRIPT_URL) {

        try {

            const scriptUrl =
                new URL(SCRIPT_URL);


            API_BASE =
                scriptUrl.protocol +
                "//" +
                scriptUrl.host +
                "/api/v1";


            STATIC_BASE =
                scriptUrl.protocol +
                "//" +
                scriptUrl.host +
                "/static";


            console.log(
                "KNOWA AI Widget loaded from:",
                SCRIPT_URL
            );


            console.log(
                "Using API base:",
                API_BASE
            );


            console.log(
                "Using static base:",
                STATIC_BASE
            );

        } catch (error) {

            console.warn(
                "Could not determine widget URL:",
                error
            );

        }

    }


    // ============================================================
    // LOGO URL
    // ============================================================

    function resolveLogoUrl(url) {

        if (!url) {

            return (
                STATIC_BASE +
                "/knowa-logo.jpg"
            );

        }


        if (
            url.startsWith("http://") ||
            url.startsWith("https://")
        ) {

            return url;

        }


        if (url.startsWith("/")) {

            return (
                new URL(
                    url,
                    window.location.origin
                ).href
            );

        }


        return (
            STATIC_BASE +
            "/" +
            url.replace(/^\/+/, "")
        );

    }


    const LOGO_URL =
        resolveLogoUrl(
            CONFIGURED_LOGO_URL
        );


    console.log(
        "KNOWA AI configured logo:",
        CONFIGURED_LOGO_URL
    );


    console.log(
        "KNOWA AI final logo URL:",
        LOGO_URL
    );


    // ============================================================
    // PREVENT DUPLICATE WIDGET
    // ============================================================

    if (
        document.getElementById(
            "knowa-ai-widget"
        )
    ) {

        console.log(
            "KNOWA AI Widget already loaded."
        );

        return;

    }


    // ============================================================
    // CONVERSATION HISTORY
    // ============================================================

    let conversationHistory = [];


    // ============================================================
    // CREATE CONTAINER
    // ============================================================

    const container =
        document.createElement("div");


    container.id =
        "knowa-ai-widget";


    // ============================================================
    // WIDGET HTML
    // ============================================================

    container.innerHTML = `

        <style>

            /* ==================================================
               FLOATING BUTTON
            ================================================== */

            #eai-chat-button {

                position: fixed;

                right: 20px;
                bottom: 20px;

                width: 60px;
                height: 60px;

                border: none;

                border-radius: 50%;

                background: __PRIMARY_COLOR__;

                color: white;

                cursor: pointer;

                box-shadow:
                    0 4px 15px
                    rgba(0, 0, 0, 0.2);

                z-index: 999999;

                display: flex;

                align-items: center;

                justify-content: center;

                padding: 0;

                overflow: hidden;

            }


            #eai-chat-button-logo {

                width: 38px;
                height: 38px;

                object-fit: contain;

                border-radius: 50%;

            }


            /* ==================================================
               CHAT WINDOW
            ================================================== */

            #eai-chat-window {

                position: fixed;

                __POSITION_CSS__

                width: __WIDGET_WIDTH__;

                height: __WIDGET_HEIGHT__;

                max-width:
                    calc(100vw - 40px);

                max-height:
                    calc(100vh - 120px);

                background:
                    __SECONDARY_COLOR__;

                border-radius:
                    __BORDER_RADIUS__;

                box-shadow:
                    0 8px 30px
                    rgba(0, 0, 0, 0.2);

                display: none;

                flex-direction: column;

                overflow: hidden;

                font-family:
                    Arial,
                    sans-serif;

                z-index: 999999;

            }


            /* ==================================================
               HEADER
            ================================================== */

            #eai-chat-header {

                background:
                    __PRIMARY_COLOR__;

                color: white;

                padding: 14px 15px;

                display: flex;

                justify-content:
                    space-between;

                align-items: center;

                min-height: 60px;

                box-sizing:
                    border-box;

            }


            #eai-chat-header-brand {

                display: flex;

                align-items: center;

                gap: 10px;

                min-width: 0;

            }


            #eai-chat-header-logo {

                width: 36px;

                height: 36px;

                object-fit: contain;

                border-radius: 50%;

                background: white;

                flex-shrink: 0;

            }


            #eai-chat-header-brand-text {

                display: flex;

                flex-direction: column;

                line-height: 1.2;

                min-width: 0;

            }


            #eai-chat-header-name {

                font-size: 15px;

                font-weight: 600;

                white-space: nowrap;

                overflow: hidden;

                text-overflow: ellipsis;

            }


            #eai-chat-header-platform {

                font-size: 11px;

                color:
                    rgba(
                        255,
                        255,
                        255,
                        0.8
                    );

                margin-top: 3px;

            }


            #eai-chat-close {

                border: none;

                background:
                    transparent;

                color: white;

                font-size: 22px;

                cursor: pointer;

                padding: 4px 7px;

            }


            /* ==================================================
               MESSAGES
            ================================================== */

            #eai-chat-messages {

                flex: 1;

                padding: 15px;

                overflow-y: auto;

                background:
                    #f8fafc;

            }


            .eai-message {

                padding:
                    10px 12px;

                margin-bottom:
                    10px;

                border-radius:
                    10px;

                line-height:
                    1.5;

                word-wrap:
                    break-word;

                font-size:
                    14px;

            }


            .eai-user-message {

                background:
                    #dbeafe;

                margin-left:
                    30px;

                white-space:
                    pre-wrap;

            }


            .eai-bot-message {

                background:
                    #f1f5f9;

                margin-right:
                    30px;

                white-space:
                    normal;

            }


            .eai-bot-message h1 {

                font-size:
                    20px;

                margin:
                    8px 0;

            }


            .eai-bot-message h2 {

                font-size:
                    18px;

                margin:
                    8px 0;

            }


            .eai-bot-message h3 {

                font-size:
                    16px;

                margin:
                    8px 0;

            }


            .eai-bot-message ul {

                margin:
                    6px 0;

                padding-left:
                    22px;

            }


            .eai-bot-message ol {

                margin:
                    6px 0;

                padding-left:
                    22px;

            }


            .eai-bot-message li {

                margin-bottom:
                    4px;

            }


            .eai-bot-message strong {

                font-weight:
                    bold;

            }


            .eai-bot-message code {

                background:
                    #e2e8f0;

                padding:
                    2px 5px;

                border-radius:
                    4px;

                font-family:
                    monospace;

            }


            .eai-bot-message pre {

                background:
                    #1e293b;

                color:
                    white;

                padding:
                    12px;

                border-radius:
                    8px;

                overflow-x:
                    auto;

                white-space:
                    pre-wrap;

            }


            /* ==================================================
               INPUT
            ================================================== */

            #eai-chat-input-area {

                display:
                    flex;

                padding:
                    10px;

                border-top:
                    1px solid #e2e8f0;

                background:
                    white;

                gap:
                    8px;

            }


            #eai-chat-input {

                flex:
                    1;

                border:
                    1px solid #cbd5e1;

                border-radius:
                    8px;

                padding:
                    10px;

                outline:
                    none;

                font-size:
                    14px;

                min-width:
                    0;

            }


            #eai-chat-input:focus {

                border-color:
                    __PRIMARY_COLOR__;

            }


            #eai-chat-send {

                border:
                    none;

                border-radius:
                    8px;

                padding:
                    10px 15px;

                background:
                    __PRIMARY_COLOR__;

                color:
                    white;

                cursor:
                    pointer;

                font-weight:
                    bold;

            }


            #eai-chat-send:disabled {

                opacity:
                    0.6;

                cursor:
                    not-allowed;

            }


            /* ==================================================
               TYPING
            ================================================== */

            .eai-typing {

                font-style:
                    italic;

                color:
                    #64748b;

            }


            /* ==================================================
               FOOTER
            ================================================== */

            #eai-chat-footer {

                padding:
                    8px 15px;

                border-top:
                    1px solid #e2e8f0;

                background:
                    #f8fafc;

                text-align:
                    center;

                font-size:
                    11px;

                color:
                    #94a3b8;

            }


            /* ==================================================
               MOBILE
            ================================================== */

            @media (max-width: 600px) {

                #eai-chat-window {

                    left:
                        10px;

                    right:
                        10px;

                    bottom:
                        80px;

                    top:
                        auto;

                    width:
                        calc(100vw - 20px);

                    height:
                        calc(100vh - 110px);

                }


                #eai-chat-button {

                    right:
                        15px;

                    bottom:
                        15px;

                }

            }

        </style>


        <!-- FLOATING BUTTON -->

        <button
            id="eai-chat-button"
            aria-label="Open chat"
        >

            <img
                id="eai-chat-button-logo"
                src="${LOGO_URL}"
                alt="KNOWA AI"
            />

        </button>


        <!-- CHAT WINDOW -->

        <div id="eai-chat-window">


            <!-- HEADER -->

            <div id="eai-chat-header">

                <div id="eai-chat-header-brand">

                    <img
                        id="eai-chat-header-logo"
                        src="${LOGO_URL}"
                        alt="KNOWA AI"
                    />


                    <div id="eai-chat-header-brand-text">

                        <span
                            id="eai-chat-header-name"
                        >
                            ${CHATBOT_NAME}
                        </span>


                        <span
                            id="eai-chat-header-platform"
                        >
                            | KNOWA AI
                        </span>

                    </div>

                </div>


                <button
                    id="eai-chat-close"
                    aria-label="Close chat"
                >
                    &#10005;
                </button>

            </div>


            <!-- MESSAGES -->

            <div id="eai-chat-messages">
            </div>


            <!-- INPUT -->

            <div id="eai-chat-input-area">

                <input
                    id="eai-chat-input"
                    type="text"
                    placeholder="${PLACEHOLDER}"
                    autocomplete="off"
                />


                <button
                    id="eai-chat-send"
                >
                    Send
                </button>

            </div>


            <!-- FOOTER -->

            <div id="eai-chat-footer">
                Powered by KNOWA AI
            </div>


        </div>

    `;


    // ============================================================
    // APPEND WIDGET
    // ============================================================

    document.body.appendChild(
        container
    );


    // ============================================================
    // LOGO FALLBACK
    // ============================================================

    function setupLogoFallback() {

        const logoElements = [

            document.getElementById(
                "eai-chat-button-logo"
            ),

            document.getElementById(
                "eai-chat-header-logo"
            )

        ];


        logoElements.forEach(
            function (logo) {

                if (!logo) {
                    return;
                }


                logo.addEventListener(
                    "error",
                    function () {

                        console.warn(
                            "Custom logo could not be loaded. Falling back to KNOWA logo."
                        );


                        logo.src =
                            STATIC_BASE +
                            "/knowa-logo.jpg";

                    }
                );

            }
        );

    }


    setupLogoFallback();


    // ============================================================
    // ELEMENTS
    // ============================================================

    const chatButton =
        document.getElementById(
            "eai-chat-button"
        );


    const chatWindow =
        document.getElementById(
            "eai-chat-window"
        );


    const closeButton =
        document.getElementById(
            "eai-chat-close"
        );


    const messages =
        document.getElementById(
            "eai-chat-messages"
        );


    const input =
        document.getElementById(
            "eai-chat-input"
        );


    const sendButton =
        document.getElementById(
            "eai-chat-send"
        );


    // ============================================================
    // OPEN CHAT
    // ============================================================

    chatButton.addEventListener(
        "click",
        function () {

            chatWindow.style.display =
                "flex";

            input.focus();

        }
    );


    // ============================================================
    // CLOSE CHAT
    // ============================================================

    closeButton.addEventListener(
        "click",
        function () {

            chatWindow.style.display =
                "none";

        }
    );


    // ============================================================
    // ESCAPE HTML
    // ============================================================

    function escapeHtml(text) {

        const div =
            document.createElement(
                "div"
            );


        div.textContent =
            text;


        return div.innerHTML;

    }


    // ============================================================
    // MARKDOWN RENDERER
    // ============================================================

    function renderMarkdown(text) {

        let html =
            escapeHtml(
                text
            );


        // Code blocks

        html = html.replace(
            /```(?:[a-zA-Z0-9_+-]+)?\n?([\s\S]*?)```/g,
            "<pre><code>$1</code></pre>"
        );


        // Headings

        html = html.replace(
            /^### (.*)$/gm,
            "<h3>$1</h3>"
        );


        html = html.replace(
            /^## (.*)$/gm,
            "<h2>$1</h2>"
        );


        html = html.replace(
            /^# (.*)$/gm,
            "<h1>$1</h1>"
        );


        // Bold

        html = html.replace(
            /\*\*(.*?)\*\*/g,
            "<strong>$1</strong>"
        );


        // Inline code

        html = html.replace(
            /`([^`\n]+)`/g,
            "<code>$1</code>"
        );


        const lines =
            html.split("\n");


        const result = [];


        let inUl = false;

        let inOl = false;


        for (
            let i = 0;
            i < lines.length;
            i++
        ) {

            const line =
                lines[i];


            const ulMatch =
                line.match(
                    /^\s*[-*]\s+(.*)$/
                );


            const olMatch =
                line.match(
                    /^\s*\d+\.\s+(.*)$/
                );


            if (ulMatch) {

                if (!inUl) {

                    result.push(
                        "<ul>"
                    );

                    inUl = true;

                }


                result.push(
                    "<li>" +
                    ulMatch[1] +
                    "</li>"
                );


                continue;

            }


            if (olMatch) {

                if (!inOl) {

                    result.push(
                        "<ol>"
                    );

                    inOl = true;

                }


                result.push(
                    "<li>" +
                    olMatch[1] +
                    "</li>"
                );


                continue;

            }


            if (inUl) {

                result.push(
                    "</ul>"
                );

                inUl = false;

            }


            if (inOl) {

                result.push(
                    "</ol>"
                );

                inOl = false;

            }


            if (
                line.trim() === ""
            ) {

                result.push(
                    "<br>"
                );

            } else {

                result.push(
                    "<span>" +
                    line +
                    "</span><br>"
                );

            }

        }


        if (inUl) {

            result.push(
                "</ul>"
            );

        }


        if (inOl) {

            result.push(
                "</ol>"
            );

        }


        return result.join("");

    }


    // ============================================================
    // ADD MESSAGE
    // ============================================================

    function addMessage(
        text,
        type
    ) {

        const message =
            document.createElement(
                "div"
            );


        message.className =
            "eai-message " +
            (
                type === "user"
                    ? "eai-user-message"
                    : "eai-bot-message"
            );


        if (type === "bot") {

            message.innerHTML =
                renderMarkdown(
                    text
                );

        } else {

            message.textContent =
                text;

        }


        messages.appendChild(
            message
        );


        messages.scrollTop =
            messages.scrollHeight;


        return message;

    }


    // ============================================================
    // WELCOME MESSAGE
    // ============================================================

    addMessage(
        WELCOME_MESSAGE,
        "bot"
    );


    // ============================================================
    // SEND MESSAGE
    // ============================================================

    async function sendMessage() {

        const text =
            input.value.trim();


        if (
            !text ||
            sendButton.disabled
        ) {

            return;

        }


        // Show user message

        addMessage(
            text,
            "user"
        );


        input.value = "";


        sendButton.disabled =
            true;


        // Typing indicator

        const typingMessage =
            addMessage(
                "Typing...",
                "bot"
            );


        typingMessage.classList.add(
            "eai-typing"
        );


        try {

            // ====================================================
            // REQUEST BODY
            // ====================================================

            const requestBody = {

                embed_token:
                    EMBED_TOKEN,

                query:
                    text,

                conversation_history:
                    conversationHistory

            };


            console.log(
                "Sending widget request:",
                requestBody
            );


            // ====================================================
            // API REQUEST
            // ====================================================

            const response =
                await fetch(
                    API_BASE +
                    "/widget/chat",
                    {

                        method:
                            "POST",

                        headers: {

                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json"

                        },

                        body:
                            JSON.stringify(
                                requestBody
                            )

                    }
                );


            // ====================================================
            // RESPONSE
            // ====================================================

            let data = {};


            try {

                data =
                    await response.json();

            } catch (error) {

                console.error(
                    "Failed to parse widget response:",
                    error
                );

            }


            typingMessage.remove();


            // ====================================================
            // ERROR
            // ====================================================

            if (!response.ok) {

                console.error(
                    "Widget API error:",
                    data
                );


                addMessage(
                    data.detail ||
                    "Unable to get a response from the AI.",
                    "bot"
                );


                return;

            }


            // ====================================================
            // ANSWER
            // ====================================================

            const answer =
                data.answer ||
                "I couldn't generate an answer.";


            addMessage(
                answer,
                "bot"
            );


            // ====================================================
            // CONVERSATION HISTORY
            // ====================================================

            conversationHistory.push({

                role:
                    "user",

                content:
                    text

            });


            conversationHistory.push({

                role:
                    "assistant",

                content:
                    answer

            });


        } catch (error) {

            console.error(
                "Widget chat error:",
                error
            );


            typingMessage.remove();


            addMessage(
                "Sorry, I couldn't connect to the AI server.",
                "bot"
            );

        } finally {

            sendButton.disabled =
                false;

            input.focus();

        }

    }


    // ============================================================
    // SEND BUTTON
    // ============================================================

    sendButton.addEventListener(
        "click",
        sendMessage
    );


    // ============================================================
    // ENTER KEY
    // ============================================================

    input.addEventListener(
        "keydown",
        function (event) {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                sendMessage();

            }

        }
    );


    // ============================================================
    // READY
    // ============================================================

    console.log(
        "KNOWA AI Widget ready."
    );

})();
"""

    # ============================================================
    # POSITION CSS
    # ============================================================

    position_css = (
        "right: 20px; bottom: 90px;"
    )

    if position == "bottom-left":
        position_css = (
            "left: 20px; bottom: 90px;"
        )

    elif position == "top-right":
        position_css = (
            "right: 20px; top: 90px;"
        )

    elif position == "top-left":
        position_css = (
            "left: 20px; top: 90px;"
        )

    # ============================================================
    # INSERT VALUES
    # ============================================================

    js = js.replace(
        "__EMBED_TOKEN__",
        js_embed_token,
    )

    js = js.replace(
        "__CHATBOT_NAME__",
        js_chatbot_name,
    )

    js = js.replace(
        "__WELCOME_MESSAGE__",
        js_welcome_message,
    )

    js = js.replace(
        "__PLACEHOLDER__",
        js_placeholder,
    )

    js = js.replace(
        "__LOGO_URL__",
        js_logo_url,
    )

    js = js.replace(
        "__PRIMARY_COLOR__",
        primary_color,
    )

    js = js.replace(
        "__SECONDARY_COLOR__",
        secondary_color,
    )

    js = js.replace(
        "__WIDGET_WIDTH__",
        widget_width,
    )

    js = js.replace(
        "__WIDGET_HEIGHT__",
        widget_height,
    )

    js = js.replace(
        "__BORDER_RADIUS__",
        border_radius,
    )

    js = js.replace(
        "__POSITION_CSS__",
        position_css,
    )

    # ============================================================
    # RETURN JAVASCRIPT
    # ============================================================

    return Response(
        content=js,
        media_type="application/javascript",
        headers={
            "Cache-Control":
                "no-cache, no-store, must-revalidate",

            "Pragma":
                "no-cache",

            "Expires":
                "0",
        },
    )