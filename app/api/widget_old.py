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
    Generate the JavaScript chatbot widget dynamically.

    The widget:
    - Uses the chatbot embed token
    - Loads chatbot settings
    - Sends queries to /api/v1/widget/chat
    - Maintains conversation history during the current page session
    - Supports markdown-like formatting in bot responses
    """

    # ============================================================
    # FIND CHATBOT
    # ============================================================

    chatbot = (
        db.query(Chatbot)
        .filter(Chatbot.embed_token == embed_token)
        .first()
    )

    if chatbot is None:
        raise HTTPException(
            status_code=404,
            detail="Invalid embed token",
        )

    # ============================================================
    # FIND CHATBOT SETTINGS
    # ============================================================

    settings = (
        db.query(ChatbotSettings)
        .filter(ChatbotSettings.chatbot_id == chatbot.id)
        .first()
    )

    if settings is None:
        raise HTTPException(
            status_code=404,
            detail="Settings not found",
        )

    # ============================================================
    # SAFELY PREPARE PYTHON VALUES
    # ============================================================

    # repr() creates valid JavaScript string literals.
    js_embed_token = repr(chatbot.embed_token)
    js_name = repr(chatbot.name or "My Bot")
    js_welcome = repr(
        settings.welcome_message
        or "Hi! How can I help you today?"
    )
    js_placeholder = repr(
        settings.placeholder
        or "Ask me anything..."
    )

    primary_color = settings.primary_color or "#2563eb"
    widget_width = settings.widget_width or "380px"
    widget_height = settings.widget_height or "600px"
    border_radius = settings.border_radius or "16px"

    # ============================================================
    # JAVASCRIPT WIDGET
    # ============================================================

    js = f"""
(function () {{

    "use strict";

    // ============================================================
    // EMBED TOKEN
    // ============================================================

    const EMBED_TOKEN = {js_embed_token};

    console.log(
        "Widget initialized with embed token:",
        EMBED_TOKEN
    );


    // ============================================================
    // DETERMINE SCRIPT URL
    // ============================================================

    const SCRIPT_URL = document.currentScript
        ? document.currentScript.src
        : "";


    // ============================================================
    // DETERMINE API BASE URL
    // ============================================================

    let API_BASE = "http://localhost:8000/api/v1";
    let STATIC_BASE = "http://localhost:8000/static";

    if (SCRIPT_URL) {{

        try {{

            const scriptUrl = new URL(SCRIPT_URL);

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
                "Widget loaded from:",
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

        }} catch (error) {{

            console.warn(
                "Could not determine API base URL:",
                error
            );

        }}

    }}


    // ============================================================
    // PREVENT DUPLICATE WIDGET
    // ============================================================

    if (
        document.getElementById(
            "knowa-ai-widget"
        )
    ) {{

        console.log(
            "KNOWA AI Widget already loaded."
        );

        return;
    }}


    // ============================================================
    // CONVERSATION HISTORY
    //
    // This exists only while the current page is open.
    // Refreshing the page clears it.
    // ============================================================

    let conversationHistory = [];


    // ============================================================
    // CONTAINER
    // ============================================================

    const container =
        document.createElement("div");

    container.id =
        "knowa-ai-widget";


    // ============================================================
    // WIDGET HTML + CSS
    // ============================================================

    container.innerHTML = `
        <style>

            #eai-chat-button {{
                position: fixed;
                right: 20px;
                bottom: 20px;

                width: 60px;
                height: 60px;

                border: none;
                border-radius: 50%;

                background: {primary_color};
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
            }}

            #eai-chat-button img {{
                width: 36px;
                height: 36px;
                object-fit: contain;
            }}


            #eai-chat-window {{
                position: fixed;

                right: 20px;
                bottom: 90px;

                width: {widget_width};
                height: {widget_height};

                max-width:
                    calc(100vw - 40px);

                max-height:
                    calc(100vh - 120px);

                background: white;

                border-radius: {border_radius};

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
            }}


            #eai-chat-header {{
                background: {primary_color};

                color: white;

                padding: 15px;

                display: flex;

                justify-content:
                    space-between;

                align-items: center;

                font-weight: bold;
            }}

            #eai-chat-header-brand {{
                display: flex;
                align-items: center;
                gap: 10px;
            }}

            #eai-chat-header-logo {{
                width: 32px;
                height: 32px;
                object-fit: contain;
            }}

            #eai-chat-header-brand > div {{
                display: flex;
                flex-direction: column;
                line-height: 1.2;
            }}

            #eai-chat-header-name {{
                font-size: 15px;
                font-weight: 600;
            }}

            #eai-chat-header-platform {{
                font-size: 11px;
                color: rgba(255, 255, 255, 0.8);
            }}


            #eai-chat-close {{
                border: none;

                background: transparent;

                color: white;

                font-size: 20px;

                cursor: pointer;
            }}


            #eai-chat-messages {{
                flex: 1;

                padding: 15px;

                overflow-y: auto;

                background: #f8fafc;
            }}


            .eai-message {{
                padding: 10px 12px;

                margin-bottom: 10px;

                border-radius: 10px;

                line-height: 1.5;

                word-wrap: break-word;
            }}


            .eai-user-message {{
                background: #dbeafe;

                margin-left: 30px;

                white-space: pre-wrap;
            }}


            .eai-bot-message {{
                background: #f1f5f9;

                margin-right: 30px;

                white-space: normal;
            }}


            .eai-bot-message h1 {{
                font-size: 20px;
                margin: 8px 0;
            }}


            .eai-bot-message h2 {{
                font-size: 18px;
                margin: 8px 0;
            }}


            .eai-bot-message h3 {{
                font-size: 16px;
                margin: 8px 0;
            }}


            .eai-bot-message ul {{
                margin: 6px 0;
                padding-left: 22px;
            }}


            .eai-bot-message ol {{
                margin: 6px 0;
                padding-left: 22px;
            }}


            .eai-bot-message li {{
                margin-bottom: 4px;
            }}


            .eai-bot-message strong {{
                font-weight: bold;
            }}


            .eai-bot-message code {{
                background: #e2e8f0;

                padding: 2px 5px;

                border-radius: 4px;

                font-family: monospace;
            }}


            .eai-bot-message pre {{
                background: #1e293b;

                color: white;

                padding: 12px;

                border-radius: 8px;

                overflow-x: auto;

                white-space: pre-wrap;
            }}


            #eai-chat-input-area {{
                display: flex;

                padding: 10px;

                border-top:
                    1px solid #e2e8f0;

                background: white;

                gap: 8px;
            }}


            #eai-chat-input {{
                flex: 1;

                border:
                    1px solid #cbd5e1;

                border-radius: 8px;

                padding: 10px;

                outline: none;

                font-size: 14px;
            }}


            #eai-chat-input:focus {{
                border-color: {primary_color};
            }}


            #eai-chat-send {{
                border: none;

                border-radius: 8px;

                padding: 10px 15px;

                background: {primary_color};

                color: white;

                cursor: pointer;

                font-weight: bold;
            }}


            #eai-chat-send:disabled {{
                opacity: 0.6;

                cursor: not-allowed;
            }}


            .eai-typing {{
                font-style: italic;

                color: #64748b;
            }}

            #eai-chat-footer {{
                padding: 8px 15px;
                border-top: 1px solid #e2e8f0;
                background: #f8fafc;
                text-align: center;
                font-size: 11px;
                color: #94a3b8;
            }}


            @media (max-width: 600px) {{

                #eai-chat-window {{
                    right: 10px;

                    bottom: 80px;

                    width:
                        calc(100vw - 20px);

                    height:
                        calc(100vh - 110px);
                }}


                #eai-chat-button {{
                    right: 15px;

                    bottom: 15px;
                }}

            }}

        </style>


        <button
            id="eai-chat-button"
            aria-label="Open chat"
        >
            <img src="${{STATIC_BASE}}/knowa-logo.jpg" alt="KNOWA AI" />
        </button>


        <div id="eai-chat-window">

            <div id="eai-chat-header">

                <div id="eai-chat-header-brand">
                    <img id="eai-chat-header-logo" src="${{STATIC_BASE}}/knowa-logo.jpg" alt="KNOWA AI" />
                    <div>
                        <span id="eai-chat-header-name">{js_name}</span>
                        <span id="eai-chat-header-platform">| KNOWA AI</span>
                    </div>
                </div>

                <button
                    id="eai-chat-close"
                    aria-label="Close chat"
                >
                    &#10005;
                </button>

            </div>


            <div id="eai-chat-messages"></div>


            <div id="eai-chat-input-area">

                <input
                    id="eai-chat-input"
                    type="text"
                    placeholder={js_placeholder}
                    autocomplete="off"
                />


                <button id="eai-chat-send">
                    Send
                </button>

            </div>

            <div id="eai-chat-footer">
                Powered by KNOWA AI
            </div>

        </div>
    `;


    document.body.appendChild(container);


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
        function () {{

            chatWindow.style.display = "flex";

            input.focus();

        }}
    );


    // ============================================================
    // CLOSE CHAT
    // ============================================================

    closeButton.addEventListener(
        "click",
        function () {{

            chatWindow.style.display = "none";

        }}
    );


    // ============================================================
    // ESCAPE HTML
    // ============================================================

    function escapeHtml(text) {{

        const div =
            document.createElement("div");

        div.textContent = text;

        return div.innerHTML;
    }}


    // ============================================================
    // MARKDOWN RENDERER
    // ============================================================

    function renderMarkdown(text) {{

        let html =
            escapeHtml(text);


        // Code blocks

        html = html.replace(
            /```(?:[a-zA-Z0-9_+-]+)?\\n?([\\s\\S]*?)```/g,
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
            /\\*\\*(.*?)\\*\\*/g,
            "<strong>$1</strong>"
        );


        // Inline code

        html = html.replace(
            /`([^`\\n]+)`/g,
            "<code>$1</code>"
        );


        const lines =
            html.split("\\n");


        const result = [];

        let inUl = false;

        let inOl = false;


        for (
            let i = 0;
            i < lines.length;
            i++
        ) {{

            const line =
                lines[i];


            const ulMatch =
                line.match(
                    /^\\s*[-*]\\s+(.*)$/
                );


            const olMatch =
                line.match(
                    /^\\s*\\d+\\.\\s+(.*)$/
                );


            if (ulMatch) {{

                if (!inUl) {{

                    result.push("<ul>");

                    inUl = true;

                }}


                result.push(
                    "<li>" +
                    ulMatch[1] +
                    "</li>"
                );


                continue;
            }}


            if (olMatch) {{

                if (!inOl) {{

                    result.push("<ol>");

                    inOl = true;

                }}


                result.push(
                    "<li>" +
                    olMatch[1] +
                    "</li>"
                );


                continue;
            }}


            if (inUl) {{

                result.push("</ul>");

                inUl = false;

            }}


            if (inOl) {{

                result.push("</ol>");

                inOl = false;

            }}


            if (
                line.trim() === ""
            ) {{

                result.push("<br>");

            }} else {{

                result.push(
                    "<span>" +
                    line +
                    "</span><br>"
                );

            }}

        }}


        if (inUl) {{

            result.push("</ul>");

        }}


        if (inOl) {{

            result.push("</ol>");

        }}


        return result.join("");
    }}


    // ============================================================
    // ADD MESSAGE
    // ============================================================

    function addMessage(
        text,
        type
    ) {{

        const message =
            document.createElement("div");


        message.className =
            "eai-message " +
            (
                type === "user"
                    ? "eai-user-message"
                    : "eai-bot-message"
            );


        if (type === "bot") {{

            message.innerHTML =
                renderMarkdown(text);

        }} else {{

            message.textContent =
                text;

        }}


        messages.appendChild(
            message
        );


        messages.scrollTop =
            messages.scrollHeight;


        return message;
    }}


    // ============================================================
    // WELCOME MESSAGE
    // ============================================================

    addMessage(
        {js_welcome},
        "bot"
    );


    // ============================================================
    // SEND MESSAGE
    // ============================================================

    async function sendMessage() {{

        const text =
            input.value.trim();


        if (
            !text ||
            sendButton.disabled
        ) {{

            return;

        }}


        // Show user message

        addMessage(
            text,
            "user"
        );


        input.value = "";


        sendButton.disabled = true;


        // Typing indicator

        const typingMessage =
            addMessage(
                "Typing...",
                "bot"
            );


        typingMessage.classList.add(
            "eai-typing"
        );


        try {{

            // ====================================================
            // REQUEST BODY
            // ====================================================

            const requestBody = {{

                embed_token:
                    EMBED_TOKEN,

                query:
                    text,

                conversation_history:
                    conversationHistory

            }};


            console.log(
                "Sending request to:",
                API_BASE + "/widget/chat"
            );


            console.log(
                "Request payload:",
                requestBody
            );


            // ====================================================
            // API REQUEST
            // ====================================================

            const response =
                await fetch(
                    API_BASE + "/widget/chat",
                    {{

                        method: "POST",

                        headers: {{
                            "Content-Type":
                                "application/json",

                            "Accept":
                                "application/json"
                        }},

                        body:
                            JSON.stringify(
                                requestBody
                            )

                    }}
                );


            console.log(
                "Response status:",
                response.status
            );


            // ====================================================
            // PARSE RESPONSE
            // ====================================================

            let data = {{}};


            try {{

                data =
                    await response.json();

            }} catch (jsonError) {{

                console.error(
                    "Failed to parse API response:",
                    jsonError
                );

            }}


            // Remove typing indicator

            typingMessage.remove();


            // ====================================================
            // HANDLE ERROR
            // ====================================================

            if (!response.ok) {{

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
            }}


            // ====================================================
            // GET ANSWER
            // ====================================================

            const answer =
                data.answer ||
                "I couldn't generate an answer.";


            // ====================================================
            // DISPLAY ANSWER
            // ============================================================

            addMessage(
                answer,
                "bot"
            );


            // ====================================================
            // STORE CONVERSATION HISTORY
            // ============================================================

            conversationHistory.push({{

                role: "user",

                content: text

            }});


            conversationHistory.push({{

                role: "assistant",

                content: answer

            }});


            console.log(
                "Updated conversation history:",
                conversationHistory
            );


        }} catch (error) {{

            console.error(
                "Widget chat error:",
                error
            );


            typingMessage.remove();


            addMessage(
                "Sorry, I couldn't connect to the AI server.",
                "bot"
            );


        }} finally {{

            sendButton.disabled = false;

            input.focus();

        }}

    }}


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
        function (event) {{

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {{

                event.preventDefault();

                sendMessage();

            }}

        }}
    );


    // ============================================================
    // WIDGET READY
    // ============================================================

    console.log(
        "KNOWA AI Widget ready."
    );


}})();
"""

    # ============================================================
    # RETURN JAVASCRIPT
    # ============================================================

    return Response(
        content=js,
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )