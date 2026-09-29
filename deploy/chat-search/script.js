(function () {
    "use strict";

    var ATTACHED_FLAG = "eraChatSearchAttached";

    function debounce(fn, ms) {
        var t;
        return function () {
            var args = arguments;
            clearTimeout(t);
            t = setTimeout(function () { fn.apply(null, args); }, ms);
        };
    }

    function escapeRegExp(s) {
        return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    }

    function createInstance(container) {
        var scope = container.parentElement || document;
        var panel = null;
        var toggleBtn = null;
        var matches = [];
        var currentIndex = -1;

        function getMessageContentNodes() {
            return Array.prototype.slice.call(scope.querySelectorAll(".messageItemOld .messageContent"));
        }

        function getItemAuthorMap() {
            var items = Array.prototype.slice.call(scope.querySelectorAll(".messageItemOld"));
            var map = new Map();
            var lastAuthor = null;
            items.forEach(function (item) {
                var authorEl = item.querySelector(".messageAuthor");
                if (authorEl) {
                    lastAuthor = authorEl.textContent.trim();
                }
                var sysAuthorEl = item.querySelector(".dx-field-item-label-text.messageTimestamp");
                if (sysAuthorEl) {
                    lastAuthor = sysAuthorEl.textContent.trim();
                }
                map.set(item, lastAuthor);
            });
            return map;
        }

        function populateAuthorOptions(select) {
            var current = select.value;
            var map = getItemAuthorMap();
            var names = [];
            map.forEach(function (name) {
                if (name && names.indexOf(name) === -1) names.push(name);
            });
            names.sort();
            select.innerHTML = '<option value="">Все авторы</option>' + names.map(function (n) {
                var esc = n.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
                return '<option value="' + esc + '">' + esc + '</option>';
            }).join("");
            if (names.indexOf(current) !== -1) {
                select.value = current;
            }
        }

        function applyAuthorFilter(name) {
            var map = getItemAuthorMap();
            var items = Array.prototype.slice.call(scope.querySelectorAll(".messageItemOld"));
            items.forEach(function (item) {
                var visible = !name || map.get(item) === name;
                item.style.display = visible ? "" : "none";
            });
            Array.prototype.slice.call(scope.querySelectorAll(".messageDateWrapper")).forEach(function (dw) {
                var next = dw.nextElementSibling;
                var hasVisible = false;
                while (next && !next.classList.contains("messageDateWrapper")) {
                    if (next.classList.contains("messageItemOld") && next.style.display !== "none") {
                        hasVisible = true;
                        break;
                    }
                    next = next.nextElementSibling;
                }
                dw.style.display = hasVisible ? "" : "none";
            });
        }

        function clearHighlights() {
            getMessageContentNodes().forEach(function (el) {
                var marks = el.querySelectorAll("mark.eraChatSearchMark");
                marks.forEach(function (mark) {
                    var text = document.createTextNode(mark.textContent);
                    mark.replaceWith(text);
                });
                el.normalize();
            });
            matches = [];
            currentIndex = -1;
        }

        function highlightInNode(el, regex) {
            var found = [];
            var node = el.firstChild;
            if (!node || node.nodeType !== Node.TEXT_NODE) {
                return found;
            }
            var text = node.textContent;
            regex.lastIndex = 0;
            if (!regex.test(text)) {
                return found;
            }
            regex.lastIndex = 0;

            var frag = document.createDocumentFragment();
            var lastIndex = 0;
            var m;
            while ((m = regex.exec(text)) !== null) {
                if (m.index > lastIndex) {
                    frag.appendChild(document.createTextNode(text.slice(lastIndex, m.index)));
                }
                var mark = document.createElement("mark");
                mark.className = "eraChatSearchMark";
                mark.textContent = m[0];
                frag.appendChild(mark);
                found.push(mark);
                lastIndex = m.index + m[0].length;
                if (m[0].length === 0) {
                    regex.lastIndex++;
                }
            }
            if (lastIndex < text.length) {
                frag.appendChild(document.createTextNode(text.slice(lastIndex)));
            }
            node.replaceWith(frag);
            return found;
        }

        function updateCounter() {
            if (!panel) return;
            var counter = panel.querySelector(".eraChatSearchCounter");
            var input = panel.querySelector(".eraChatSearchInput");
            if (!counter || !input) return;
            if (!input.value) {
                counter.textContent = "";
            } else {
                counter.textContent = matches.length ? (currentIndex + 1) + "/" + matches.length : "0/0";
            }
        }

        function focusCurrent() {
            matches.forEach(function (m) { m.classList.remove("eraChatSearchCurrent"); });
            var m = matches[currentIndex];
            if (!m) return;
            m.classList.add("eraChatSearchCurrent");
            m.scrollIntoView({ block: "center", behavior: "smooth" });
        }

        function runSearch(query) {
            clearHighlights();
            var q = (query || "").trim();
            if (!q) {
                updateCounter();
                return;
            }
            var regex = new RegExp(escapeRegExp(q), "gi");
            getMessageContentNodes().forEach(function (el) {
                var found = highlightInNode(el, regex);
                matches = matches.concat(found);
            });
            if (matches.length) {
                currentIndex = 0;
                focusCurrent();
            }
            updateCounter();
        }

        function goNext(delta) {
            if (!matches.length) return;
            currentIndex = (currentIndex + delta + matches.length) % matches.length;
            focusCurrent();
            updateCounter();
        }

        function closePanel() {
            clearHighlights();
            applyAuthorFilter("");
            if (panel) {
                panel.remove();
                panel = null;
            }
        }

        function openPanel() {
            if (panel) {
                panel.querySelector(".eraChatSearchInput").focus();
                return;
            }
            panel = document.createElement("div");
            panel.className = "eraChatSearchPanel";
            panel.innerHTML =
                '<select class="eraChatSearchAuthorFilter" title="Фильтр по автору"></select>' +
                '<input type="text" class="eraChatSearchInput" placeholder="Поиск по сообщениям..." />' +
                '<span class="eraChatSearchCounter"></span>' +
                '<button type="button" class="eraChatSearchBtn eraChatSearchPrev" title="Предыдущее (Shift+Enter)">↑</button>' +
                '<button type="button" class="eraChatSearchBtn eraChatSearchNext" title="Следующее (Enter)">↓</button>' +
                '<button type="button" class="eraChatSearchBtn eraChatSearchClose" title="Закрыть (Esc)">✕</button>';
            container.appendChild(panel);

            var authorSelect = panel.querySelector(".eraChatSearchAuthorFilter");
            populateAuthorOptions(authorSelect);
            authorSelect.addEventListener("mousedown", function () { populateAuthorOptions(authorSelect); });
            authorSelect.addEventListener("change", function () { applyAuthorFilter(authorSelect.value); });

            var input = panel.querySelector(".eraChatSearchInput");
            var doSearch = debounce(function () { runSearch(input.value); }, 150);
            input.addEventListener("input", doSearch);
            input.addEventListener("keydown", function (e) {
                if (e.key === "Enter") {
                    e.preventDefault();
                    goNext(e.shiftKey ? -1 : 1);
                } else if (e.key === "Escape") {
                    closePanel();
                }
            });
            panel.querySelector(".eraChatSearchPrev").addEventListener("click", function () { goNext(-1); });
            panel.querySelector(".eraChatSearchNext").addEventListener("click", function () { goNext(1); });
            panel.querySelector(".eraChatSearchClose").addEventListener("click", closePanel);

            setTimeout(function () { input.focus(); }, 50);
        }

        toggleBtn = document.createElement("button");
        toggleBtn.type = "button";
        toggleBtn.className = "eraChatSearchToggle";
        toggleBtn.title = "Поиск по сообщениям чата";
        toggleBtn.innerHTML = "🔍";
        toggleBtn.addEventListener("click", openPanel);
        container.appendChild(toggleBtn);
    }

    function attachAll() {
        var containers = document.querySelectorAll(".chatMessageContainerOld");
        containers.forEach(function (container) {
            if (container[ATTACHED_FLAG]) return;
            container[ATTACHED_FLAG] = true;
            container.classList.add("eraChatSearchHost");
            createInstance(container);
        });
    }

    var observer = new MutationObserver(debounce(attachAll, 200));
    observer.observe(document.body, { childList: true, subtree: true });

    attachAll();
})();
