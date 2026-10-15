/* Chat client for the programming learning assistant.
 * Talks to POST /api/chat. Renders code fences and inline code.
 */
(function () {
  "use strict";

  var chat = document.getElementById("chat");
  var form = document.getElementById("composer");
  var input = document.getElementById("input");

  var sessionId = localStorage.getItem("tutor_session_id");
  if (!sessionId) {
    sessionId = "s-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("tutor_session_id", sessionId);
  }

  function escapeHtml(text) {
    var div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // Minimal, safe rendering: escape everything, then restore code blocks.
  function render(text) {
    var html = escapeHtml(text);
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, function (_, lang, code) {
      return "<pre><code>" + code.replace(/\n$/, "") + "</code></pre>";
    });
    html = html.replace(/`([^`\n]+)`/g, "<code>$1</code>");
    return html
      .split(/\n{2,}/)
      .map(function (chunk) {
        return chunk.indexOf("<pre>") === 0 ? chunk : "<p>" + chunk.replace(/\n/g, "<br>") + "</p>";
      })
      .join("");
  }

  function addMessage(text, kind) {
    var el = document.createElement("div");
    el.className = "message " + kind;
    el.innerHTML = render(text);
    chat.appendChild(el);
    chat.scrollTop = chat.scrollHeight;
  }

  function send(message) {
    if (!message.trim()) return;
    addMessage(message, "learner");
    input.value = "";
    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: message }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        addMessage(data.reply || "(no reply)", data.error ? "tutor error" : "tutor");
      })
      .catch(function () {
        addMessage(
          "Could not reach the tutor server. Check that it is still running, then try again.",
          "tutor error"
        );
      });
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    send(input.value);
  });

  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      send(input.value);
    }
  });

  document.querySelectorAll("#actions button").forEach(function (button) {
    button.addEventListener("click", function () {
      send(button.getAttribute("data-command"));
    });
  });

  addMessage(
    "Hi! I'm your programming practice partner. I won't just hand you " +
      "answers — I'll ask questions and give hints to help you figure " +
      "things out yourself.\n\nWhat would you like to work on today?\n" +
      "1. Practice a beginner Python exercise, or\n" +
      "2. Get help debugging code you wrote",
    "tutor"
  );
})();
