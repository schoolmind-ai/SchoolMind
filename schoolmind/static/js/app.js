(function () {
  const isArabic = document.documentElement.lang === "ar";
  const uiCopy = isArabic ? {
    showPassword: "إظهار",
    hidePassword: "إخفاء",
    working: "جارٍ التنفيذ…",
    you: "أنت",
    retry: "إعادة المحاولة",
    sending: "جارٍ الإرسال…",
    genericError: "حدث خطأ. حاول مرة أخرى.",
    thinking: "نور يفكر…",
    connectionError: "مشكلة في الاتصال. لم تُحفظ رسالتك.",
    shortMessage: "اكتب أربعة أحرف على الأقل.",
    cleared: "تم مسح المحادثة الظاهرة. يبقى السجل المحفوظ متاحًا بعد التحديث."
  } : {
    showPassword: "Show",
    hidePassword: "Hide",
    working: "Working…",
    you: "You",
    retry: "Retry",
    sending: "Sending…",
    genericError: "Something went wrong. Try again.",
    thinking: "Nour is thinking…",
    connectionError: "Connection problem. Your message was not saved.",
    shortMessage: "Enter at least four characters.",
    cleared: "Visible chat cleared. Saved history remains available after refresh."
  };

  function focusableWithin(container) {
    if (!container) return [];
    return Array.from(container.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'))
      .filter(function (item) { return !item.hidden && item.getClientRects().length; });
  }

  function keepFocusInside(event, container) {
    if (event.key !== "Tab") return;
    const items = focusableWithin(container);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  const main = document.querySelector("[data-page-main]");
  if (main) {
    const heading = main.querySelector("h1");
    (heading || main).setAttribute("tabindex", "-1");
  }

  document.querySelectorAll("a[href]").forEach(function (link) {
    try {
      const current = new URL(window.location.href);
      const target = new URL(link.getAttribute("href"), window.location.href);
      if (current.pathname === target.pathname && current.hash === target.hash) {
        link.classList.add("active");
        link.setAttribute("aria-current", "page");
      }
    } catch (error) {
      return;
    }
  });

  const navToggle = document.querySelector("[data-nav-toggle]");
  const nav = document.querySelector("[data-nav]");
  const navClose = document.querySelector("[data-nav-close]");
  let navReturnFocus = null;
  function setNav(open) {
    if (!nav || !navToggle) return;
    if (open) navReturnFocus = document.activeElement;
    nav.classList.toggle("open", open);
    navToggle.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.classList.toggle("nav-open", open);
    if (open) {
      window.setTimeout(function () {
        const items = focusableWithin(nav);
        const closeTarget = navClose && navClose.getClientRects().length ? navClose : null;
        (closeTarget || items[0] || nav).focus();
      }, 0);
    } else if (navReturnFocus && typeof navReturnFocus.focus === "function") {
      navReturnFocus.focus();
      navReturnFocus = null;
    }
  }
  if (navToggle && nav) {
    navToggle.setAttribute("aria-expanded", "false");
    navToggle.addEventListener("click", function () {
      setNav(!nav.classList.contains("open"));
    });
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        setNav(false);
      });
    });
    if (navClose) navClose.addEventListener("click", function () { setNav(false); });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") setNav(false);
      if (nav.classList.contains("open")) keepFocusInside(event, nav);
    });
  }

  const sidePanel = document.querySelector("[data-side-panel]");
  const sideToggle = document.querySelector("[data-side-toggle]");
  const sideClose = document.querySelector("[data-side-close]");
  const sideScrim = document.querySelector("[data-side-scrim]");
  let sideReturnFocus = null;
  function setSide(open) {
    if (!sidePanel || !sideToggle) return;
    if (open) sideReturnFocus = document.activeElement;
    sidePanel.classList.toggle("open", open);
    sideToggle.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.classList.toggle("side-open", open);
    if (sideScrim) sideScrim.hidden = !open;
    if (open) {
      window.setTimeout(function () {
        const items = focusableWithin(sidePanel);
        const closeTarget = sideClose && sideClose.getClientRects().length ? sideClose : null;
        if (!items.length && !sidePanel.hasAttribute("tabindex")) sidePanel.setAttribute("tabindex", "-1");
        (closeTarget || items[0] || sidePanel).focus();
      }, 220);
    } else if (sideReturnFocus && typeof sideReturnFocus.focus === "function") {
      sideReturnFocus.focus();
      sideReturnFocus = null;
    }
  }
  if (sidePanel && sideToggle) {
    sideToggle.addEventListener("click", function () { setSide(!sidePanel.classList.contains("open")); });
    if (sideClose) sideClose.addEventListener("click", function () { setSide(false); });
    if (sideScrim) sideScrim.addEventListener("click", function () { setSide(false); });
    sidePanel.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () { setSide(false); });
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") setSide(false);
      if (sidePanel.classList.contains("open")) keepFocusInside(event, sidePanel);
    });
  }

  const personalization = document.querySelector("[data-personalization-panel]");
  function setPersonalization(open) {
    if (!personalization) return;
    personalization.classList.toggle("open", open);
    personalization.setAttribute("aria-hidden", open ? "false" : "true");
    if (open) {
      const first = personalization.querySelector("select, input, button, a");
      if (first) first.focus();
    }
  }
  document.querySelectorAll("[data-open-personalization]").forEach(function (button) {
    button.addEventListener("click", function () { setPersonalization(true); });
  });
  document.querySelectorAll("[data-personalization-close]").forEach(function (button) {
    button.addEventListener("click", function () { setPersonalization(false); });
  });
  if (personalization) {
    personalization.addEventListener("click", function (event) {
      if (event.target === personalization) setPersonalization(false);
    });
  }
  const personalizationFields = document.querySelector("[data-personalization-fields]");
  const personalizationFieldsToggle = document.querySelector("[data-personalization-fields-toggle]");
  function setPersonalizationFields(open) {
    if (!personalization || !personalizationFieldsToggle) return;
    personalization.classList.toggle("fields-open", open);
    personalizationFieldsToggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (open && personalizationFields) {
      const firstField = personalizationFields.querySelector("select, input, button");
      if (firstField) firstField.focus();
    }
  }
  if (personalizationFieldsToggle) {
    personalizationFieldsToggle.addEventListener("click", function () {
      setPersonalizationFields(!personalization.classList.contains("fields-open"));
    });
  }

  document.querySelectorAll('input[type="password"]:not([data-password-ready])').forEach(function (input) {
    input.dataset.passwordReady = "true";
    const wrapper = document.createElement("span");
    wrapper.className = "password-field";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "password-toggle";
    toggle.textContent = uiCopy.showPassword;
    toggle.setAttribute("aria-label", uiCopy.showPassword);
    toggle.setAttribute("aria-pressed", "false");
    toggle.addEventListener("click", function () {
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      toggle.textContent = showing ? uiCopy.showPassword : uiCopy.hidePassword;
      toggle.setAttribute("aria-label", showing ? uiCopy.showPassword : uiCopy.hidePassword);
      toggle.setAttribute("aria-pressed", showing ? "false" : "true");
      input.focus();
    });
    wrapper.appendChild(toggle);
  });

  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (form.dataset.confirmed === "true") return;
      if (!window.confirm(form.dataset.confirm || uiCopy.genericError)) {
        event.preventDefault();
        return;
      }
      form.dataset.confirmed = "true";
    });
  });

  document.querySelectorAll("form:not([data-chat-form]):not([data-allow-repeat])").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (event.defaultPrevented) return;
      if (form.dataset.submitting === "true") {
        event.preventDefault();
        return;
      }
      form.dataset.submitting = "true";
      form.setAttribute("aria-busy", "true");
      window.requestAnimationFrame(function () {
        form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function (button) {
          button.disabled = true;
          if (button.tagName === "BUTTON" && button.textContent.trim()) {
            button.dataset.originalText = button.textContent;
            button.textContent = uiCopy.working;
          }
        });
      });
    });
  });

  document.querySelectorAll("[data-game-card]").forEach(function (card) {
    const score = card.querySelector("[data-game-score]");
    const submit = card.querySelector("[data-game-submit]");
    const feedback = card.querySelector("[data-game-feedback]");
    card.querySelectorAll("[data-game-option]").forEach(function (option) {
      option.addEventListener("click", function () {
        card.querySelectorAll("[data-game-option]").forEach(function (item) {
          item.classList.remove("selected");
        });
        option.classList.add("selected");
        if (score) score.value = option.dataset.score || score.value;
        if (feedback) feedback.textContent = option === card.querySelector("[data-game-option]") ? "Good choice. Save this practice when ready." : "Saved practice should reflect a safe next step. You can choose again.";
        if (submit) submit.disabled = false;
      });
    });
  });

  const chat = document.querySelector("[data-nour-chat]");
  if (!chat) return;
  const form = chat.querySelector("[data-chat-form]");
  const input = chat.querySelector("[data-chat-input]");
  const stream = chat.querySelector("[data-chat-stream]");
  const submit = chat.querySelector("[data-chat-submit]");
  const csrf = form ? form.querySelector('input[name="csrf_token"]') : null;
  let lastFailedMessage = "";

  function appendBubble(item) {
    if (!stream) return;
    const bubble = document.createElement("article");
    bubble.className = "chat-bubble " + (item.role === "nour" ? "nour" : "student");
    const head = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = item.role === "nour" ? "Nour" : uiCopy.you;
    const risk = document.createElement("span");
    risk.className = "risk " + (item.risk_level || "steady");
    risk.textContent = item.risk_level || "steady";
    head.append(name, risk);
    const body = document.createElement("p");
    body.textContent = item.message || "";
    const time = document.createElement("small");
    time.textContent = item.created_at || "";
    if (item.retry) {
      const retry = document.createElement("button");
      retry.type = "button";
      retry.className = "link-button";
      retry.textContent = uiCopy.retry;
      retry.addEventListener("click", function () {
        if (input) input.value = lastFailedMessage;
        if (form) form.requestSubmit();
      });
      bubble.append(head, body, retry, time);
      stream.appendChild(bubble);
      stream.scrollTop = stream.scrollHeight;
      return bubble;
    }
    bubble.append(head, body, time);
    stream.appendChild(bubble);
    stream.scrollTop = stream.scrollHeight;
    return bubble;
  }

  function setBusy(busy) {
    if (submit) {
      submit.disabled = busy;
      submit.dataset.originalText = submit.dataset.originalText || submit.textContent;
      submit.textContent = busy ? uiCopy.sending : submit.dataset.originalText;
    }
    chat.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function showError(message) {
    appendBubble({ role: "nour", risk_level: "watch", message: message || uiCopy.genericError, created_at: "", retry: true });
  }

  if (form && input) {
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
    input.addEventListener("input", function () { input.setCustomValidity(""); });
    form.addEventListener("submit", async function (event) {
      event.preventDefault();
      const message = input.value.trim();
      if (message.length < 4) {
        input.setCustomValidity(uiCopy.shortMessage);
        input.reportValidity();
        return;
      }
      input.setCustomValidity("");
      setBusy(true);
      const optimistic = appendBubble({ role: "student", risk_level: "steady", message: message, created_at: "" });
      input.value = "";
      const loading = appendBubble({ role: "nour", risk_level: "steady", message: uiCopy.thinking, created_at: "" });
      try {
        const response = await fetch(chat.dataset.endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRF-Token": csrf ? csrf.value : "",
          },
          body: JSON.stringify({ message }),
        });
        const payload = await response.json();
        if (loading) loading.remove();
        if (!response.ok || !payload.ok) {
          if (optimistic) optimistic.remove();
          lastFailedMessage = message;
          showError(payload.error);
          return;
        }
        if (optimistic && payload.user_message) {
          const time = optimistic.querySelector("small");
          const risk = optimistic.querySelector(".risk");
          if (time) time.textContent = payload.user_message.created_at || "";
          if (risk) {
            risk.className = "risk " + (payload.user_message.risk_level || "steady");
            risk.textContent = payload.user_message.risk_level || "steady";
          }
        }
        appendBubble(payload.nour_message);
      } catch (error) {
        if (loading) loading.remove();
        if (optimistic) optimistic.remove();
        lastFailedMessage = message;
        showError(uiCopy.connectionError);
      } finally {
        setBusy(false);
        input.focus();
      }
    });
  }

  document.querySelectorAll("[data-chat-suggestion]").forEach(function (button) {
    button.addEventListener("click", function () {
      if (!input) return;
      input.value = button.dataset.chatSuggestion || "";
      input.focus();
    });
  });
  if (stream) {
    stream.scrollTop = stream.scrollHeight;
  }
  const clearChat = document.querySelector("[data-clear-chat]");
  if (clearChat && stream) {
    clearChat.addEventListener("click", function () {
      stream.innerHTML = "";
      appendBubble({ role: "nour", risk_level: "steady", message: uiCopy.cleared, created_at: "" });
    });
  }
})();
