(function () {
    'use strict';

    // ---------- Conditional field visibility ----------
    function evaluateCondition(condition, value) {
        var operator = condition.operator || 'equals';
        var expected = condition.value;
        switch (operator) {
            case 'equals':
                return value == expected;
            case 'not_equals':
                return value != expected;
            case 'in':
                var list = Array.isArray(expected) ? expected : [];
                if (Array.isArray(value)) {
                    return value.some(function (v) { return list.some(function (e) { return e == v; }); });
                }
                return list.some(function (e) { return e == value; });
            default:
                return true;
        }
    }

    function fieldValue(element) {
        var field = element;
        var tag = field.tagName.toLowerCase();
        if (tag === 'select') {
            if (field.multiple) {
                return Array.prototype.slice.call(field.selectedOptions).map(function (o) { return o.value; });
            }
            return field.value;
        }
        if (tag === 'input' && field.type === 'checkbox') {
            return field.checked ? 'true' : 'false';
        }
        if (tag === 'input' && field.type === 'radio') {
            var checked = document.querySelector('input[name="' + field.name + '"]:checked');
            return checked ? checked.value : '';
        }
        return field.value;
    }

    function conditionMet(wrapper, form) {
        var fieldEl = wrapper.querySelector('[data-cond-depends-on]');
        if (!fieldEl) {
            return true; // no condition → always visible
        }
        var dependsOn = fieldEl.dataset.condDependsOn;
        var sourceEl = form.querySelector('[name="' + dependsOn + '"]');
        if (!sourceEl) {
            return true;
        }
        var condition = {
            operator: fieldEl.dataset.condOperator || 'equals',
            value: safeParse(fieldEl.dataset.condValue)
        };
        return evaluateCondition(condition, fieldValue(sourceEl));
    }

    function safeParse(raw) {
        if (!raw) return '';
        try {
            var parsed = JSON.parse(raw);
            return parsed;
        } catch (e) {
            return raw;
        }
    }

    function refreshConditions(container) {
        container.querySelectorAll('[data-attribute]').forEach(function (attr) {
            var fieldEl = attr.querySelector('[data-cond-depends-on]');
            if (!fieldEl) {
                attr.hidden = false;
                return;
            }
            var show = conditionMet(attr, container);
            attr.hidden = !show;
            var input = attr.querySelector('input, textarea, select');
            if (input) {
                // Hidden fields are excluded server-side on submit, so mark
                // them disabled to prevent the browser sending values.
                input.disabled = !show;
            }
        });
    }

    // ---------- Rich text (zero-dependency contenteditable widget) ----------
    function initRichText() {
        var editors = document.querySelectorAll('[data-richtext]');
        if (!editors.length) {
            return;
        }
        editors.forEach(function (textarea) {
            if (textarea.dataset.richtextReady) {
                return;
            }
            textarea.dataset.richtextReady = 'true';

            var toolbar = document.createElement('div');
            toolbar.className = 'richtext-toolbar';
            var commands = [
                ['bold', 'B'], ['italic', 'I'], ['underline', 'U'],
                ['insertUnorderedList', '\u2022 List'], ['insertOrderedList', '1. List']
            ];
            commands.forEach(function (pair) {
                var btn = document.createElement('button');
                btn.type = 'button';
                btn.textContent = pair[1];
                btn.title = pair[0];
                btn.addEventListener('mousedown', function (e) { e.preventDefault(); });
                btn.addEventListener('click', function (e) {
                    e.preventDefault();
                    contentDiv.focus();
                    document.execCommand(pair[0], false, null);
                    sync();
                });
                toolbar.appendChild(btn);
            });

            var contentDiv = document.createElement('div');
            contentDiv.className = 'richtext-editor';
            contentDiv.setAttribute('contenteditable', 'true');
            contentDiv.innerHTML = textarea.value || '';

            function sync() {
                textarea.value = contentDiv.innerHTML;
            }
            contentDiv.addEventListener('input', sync);

            textarea.hidden = true;
            textarea.closest('.field') && textarea.closest('.field').classList.add('has-richtext');
            textarea.parentNode.insertBefore(toolbar, textarea.nextSibling);
            textarea.parentNode.insertBefore(contentDiv, toolbar.nextSibling);
        });
    }

    // ---------- Boot ----------
    document.addEventListener('DOMContentLoaded', function () {
        var form = document.querySelector('[data-conditional-form]');
        if (form) {
            // Include hidden/disabled fields' display via refreshConditions on load + change.
            refreshConditions(form);
            form.addEventListener('change', function (e) {
                if (e.target.matches('select, input[type="checkbox"], input[type="radio"]')) {
                    refreshConditions(form);
                }
            });
        }
        initRichText();
    });

    // Re-initialize rich text widgets after the DOM settles (covers widgets
    // inserted dynamically by refreshConditions-based rendering).
    window.addEventListener('load', initRichText);
})();