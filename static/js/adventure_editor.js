/**
 * Teacher Adventures map editor (vanilla JS + SVG).
 */
(function () {
  "use strict";

  var NODE_TYPES = ["start", "story", "battle", "quiz", "choice", "end"];
  var ALL_NODE_TYPES = ["start", "story", "battle", "quiz", "choice", "reward", "milestone", "boss", "end"];
  var DEFAULT_ICONS = {
    start: "flag",
    story: "auto_stories",
    battle: "swords",
    quiz: "quiz",
    choice: "alt_route",
    reward: "redeem",
    milestone: "emoji_events",
    boss: "cruelty_free",
    end: "sports_score",
  };

  function iconCatalog() {
    var root = document.getElementById("adventure-editor");
    if (!root) return [];
    try {
      var raw = root.getAttribute("data-icon-catalog");
      return raw ? JSON.parse(raw) : [];
    } catch (err) {
      return [];
    }
  }

  function defaultIconFor(nodeType) {
    var found = iconCatalog().find(function (icon) {
      return (icon.default_for || []).indexOf(nodeType) >= 0;
    });
    return (found && found.ligature) || DEFAULT_ICONS[nodeType] || "flag";
  }

  function resolveNodeIcon(node) {
    if (node && node.icon_url && node.icon_url.charAt(0) !== "/") return node.icon_url;
    return defaultIconFor(node && node.node_type);
  }

  function recordCommand(entry) {
    if (window.AdventureEditorCommands && AdventureEditorCommands.record) {
      AdventureEditorCommands.record(entry);
    }
  }

  function nodeRecreatePayload(node) {
    return {
      slug: node.slug,
      title: node.title,
      description: node.description || null,
      lore: node.lore || null,
      icon_url: node.icon_url || null,
      node_type: node.node_type,
      x: node.x,
      y: node.y,
      is_optional: !!node.is_optional,
      is_start: node.node_type === "start" || !!node.is_start,
      is_end: node.node_type === "end" || !!node.is_end,
      question_set_id: node.question_set_id || null,
      monster_id: node.monster_id || null,
    };
  }

  var editorState = {
    adventureId: null,
    canEdit: true,
    adventure: null,
    nodes: [],
    edges: [],
    validation: null,
    monsters: [],
    questionSets: [],
    selectedNodeId: null,
  };

  var editorStatusHideTimer = null;

  var GRID_BACKGROUND =
    "radial-gradient(circle, rgba(148, 163, 184, 0.25) 1px, transparent 1px)";

  function applyCanvasBackground(url) {
    var wrap = document.querySelector(".editor-canvas-wrap");
    if (!wrap) return;
    if (url) {
      wrap.style.backgroundImage = "url(\"" + url + "\"), " + GRID_BACKGROUND;
      wrap.style.backgroundSize = "cover, 24px 24px";
      wrap.classList.add("has-custom-background");
    } else {
      wrap.style.backgroundImage = GRID_BACKGROUND;
      wrap.style.backgroundSize = "24px 24px";
      wrap.classList.remove("has-custom-background");
    }
  }

  function uploadBackgroundFile(adventureId, file) {
    var form = new FormData();
    form.append("file", file);
    return fetch("/teacher/adventures/" + adventureId + "/background", {
      method: "POST",
      body: form,
    }).then(function (res) {
      return res.text().then(function (text) {
        var parsed;
        try {
          parsed = text ? JSON.parse(text) : {};
        } catch (parseErr) {
          return {
            success: false,
            message: res.ok ? "Invalid server response." : (res.statusText || "Upload failed."),
          };
        }
        if (!res.ok && parsed.success !== false) {
          parsed.success = false;
          if (!parsed.message) parsed.message = res.statusText || "Upload failed.";
        }
        return parsed;
      });
    }).catch(function (err) {
      return {
        success: false,
        message: err.message || "Network error during upload.",
      };
    });
  }

  function formatApiErrorMessage(body, fallback) {
    if (!body) return fallback || "Request failed.";
    if (body.errors && body.errors.length) {
      return body.errors.map(function (e) { return e.message || String(e); }).join(" ");
    }
    return body.message || fallback || "Request failed.";
  }

  function getOrCreateEditorStatusEl() {
    var el = document.getElementById("editor-status");
    if (el) return el;
    el = document.createElement("div");
    el.id = "editor-status";
    el.className = "editor-status alert d-none";
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    var anchor = document.getElementById("editor-validation");
    if (anchor && anchor.parentNode) {
      anchor.parentNode.insertBefore(el, anchor);
    } else {
      var root = document.getElementById("adventure-editor");
      if (root) root.insertBefore(el, root.firstChild);
    }
    return el;
  }

  function showEditorError(message) {
    var el = document.getElementById("editor-validation");
    if (!el || !message) return;
    el.className = "alert alert-danger";
    el.textContent = message;
    el.classList.remove("d-none");
  }

  function showEditorSuccess(message) {
    if (!message) return;
    var el = getOrCreateEditorStatusEl();
    el.className = "editor-status alert alert-success";
    el.textContent = message;
    el.classList.remove("d-none");
    if (editorStatusHideTimer) clearTimeout(editorStatusHideTimer);
    editorStatusHideTimer = setTimeout(function () {
      el.classList.add("d-none");
    }, 4000);
  }

  function updatePublishValidationBanner(validation) {
    var el = document.getElementById("editor-validation");
    if (!el) return;
    editorState.validation = validation || null;
    var messages = [];
    if (validation) {
      (validation.errors || []).forEach(function (e) {
        if (e.message) messages.push(e.message);
      });
      (validation.warnings || []).forEach(function (e) {
        if (e.message) messages.push(e.message);
      });
    }
    (editorState.nodes || []).forEach(function (node) {
      if (node.node_type !== "quiz" || !node.question_set_id) return;
      var available = (editorState.questionSets || []).some(function (qs) {
        return qs.id === node.question_set_id;
      });
      if (!available) {
        messages.push(
          "Quiz node \"" + node.slug + "\" uses a question set that is unavailable; pick your own."
        );
      }
    });
    if (!messages.length) {
      el.classList.add("d-none");
      el.textContent = "";
      return;
    }
    var blocking = validation && !validation.ok_to_publish;
    el.className = blocking ? "alert alert-warning" : "alert alert-info";
    el.classList.remove("d-none");
    el.textContent = (blocking ? "Before publishing: " : "Publish readiness: ") + messages.join(" ");
  }

  function applyGraphPayload(data) {
    if (!data) return;
    if (data.adventure) {
      editorState.adventure = data.adventure;
    }
    editorState.nodes = data.nodes || [];
    editorState.edges = data.edges || [];
    if (data.validation !== undefined) {
      editorState.validation = data.validation;
    }
  }

  function getGraphSnapshot() {
    return {
      adventure: editorState.adventure,
      nodes: editorState.nodes,
      edges: editorState.edges,
      validation: editorState.validation,
    };
  }

  function updateAdventureInState(adventure) {
    if (!adventure) return;
    editorState.adventure = Object.assign({}, editorState.adventure || {}, adventure);
  }

  function updateNodeInState(node) {
    if (!node || node.id == null) return;
    var idx = editorState.nodes.findIndex(function (n) { return n.id === node.id; });
    if (idx >= 0) editorState.nodes[idx] = node;
    else editorState.nodes.push(node);
  }

  function removeNodeFromState(nodeId) {
    editorState.nodes = editorState.nodes.filter(function (n) { return n.id !== nodeId; });
    editorState.edges = editorState.edges.filter(function (e) {
      return e.from_node_id !== nodeId && e.to_node_id !== nodeId;
    });
    if (editorState.selectedNodeId === nodeId) editorState.selectedNodeId = null;
  }

  function updateEdgeInState(edge) {
    if (!edge || edge.id == null) return;
    var idx = editorState.edges.findIndex(function (e) { return e.id === edge.id; });
    if (idx >= 0) editorState.edges[idx] = edge;
    else editorState.edges.push(edge);
  }

  function removeEdgeFromState(edgeId) {
    editorState.edges = editorState.edges.filter(function (e) { return e.id !== edgeId; });
  }

  async function api(method, url, body) {
    var opts = { method: method, headers: { "Content-Type": "application/json" } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    try {
      var res = await fetch(url, opts);
      var text = await res.text();
      var parsed;
      try {
        parsed = text ? JSON.parse(text) : {};
      } catch (parseErr) {
        return {
          success: false,
          message: res.ok ? "Invalid server response." : (res.statusText || "Request failed."),
          errors: [{ message: "Could not parse server response as JSON." }],
          _httpStatus: res.status,
        };
      }
      if (typeof parsed !== "object" || parsed === null) {
        return {
          success: false,
          message: "Invalid server response.",
          errors: [{ message: "Server returned an unexpected response." }],
          _httpStatus: res.status,
        };
      }
      if (!res.ok && parsed.success !== false) {
        parsed.success = false;
        if (!parsed.message && !(parsed.errors && parsed.errors.length)) {
          parsed.message = res.statusText || "Request failed.";
        }
      }
      parsed._httpStatus = res.status;
      return parsed;
    } catch (fetchErr) {
      return {
        success: false,
        message: "Network error. Check your connection and try again.",
        errors: [{ message: fetchErr.message || "Fetch failed." }],
      };
    }
  }

  function svgPoint(svg, evt) {
    var pt = svg.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    var ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    var loc = pt.matrixTransform(ctm.inverse());
    return { x: Math.max(0, loc.x), y: Math.max(0, loc.y) };
  }

  function makeSlug(type, nodes) {
    var base = type;
    var slug = base;
    var n = 2;
    var existing = (nodes || []).map(function (nd) { return nd.slug; });
    while (existing.indexOf(slug) >= 0) {
      slug = base + "-" + n;
      n += 1;
    }
    return slug;
  }

  function titleForType(type) {
    return type.charAt(0).toUpperCase() + type.slice(1);
  }

  function edgeClass(edge) {
    var cls = "edge-line";
    if (edge.condition_type === "choice") cls += " edge-choice";
    if (edge.condition_type === "criteria") cls += " edge-criteria";
    if (edge.unlock_semantics === "or") cls += " edge-or";
    return cls;
  }

  var DRAG_THRESHOLD_PX = 4;

  function getMapBounds(data) {
    var adv = (data && data.adventure) || editorState.adventure || {};
    var width = adv.width;
    var height = adv.height;
    if (!width || !height) {
      var svg = document.getElementById("adventure-canvas");
      if (svg) {
        width = parseInt(svg.getAttribute("width"), 10) || 2000;
        height = parseInt(svg.getAttribute("height"), 10) || 1500;
      } else {
        width = 2000;
        height = 1500;
      }
    }
    return { width: width, height: height };
  }

  function clampNodePosition(x, y, bounds) {
    return {
      x: Math.max(0, Math.min(bounds.width, Math.round(x))),
      y: Math.max(0, Math.min(bounds.height, Math.round(y))),
    };
  }

  function setNodeGroupPosition(g, x, y) {
    g.setAttribute("transform", "translate(" + x + "," + y + ")");
  }

  function updateEdgeEndpointsForNode(svg, nodeId, x, y) {
    if (!svg) return;
    (editorState.edges || []).forEach(function (edge) {
      var line = svg.querySelector('line[data-edge-id="' + edge.id + '"]');
      if (!line) return;
      if (edge.from_node_id === nodeId) {
        line.setAttribute("x1", x);
        line.setAttribute("y1", y);
      }
      if (edge.to_node_id === nodeId) {
        line.setAttribute("x2", x);
        line.setAttribute("y2", y);
      }
      var label = svg.querySelector('text[data-edge-id="' + edge.id + '"]');
      if (label) {
        var x1 = parseFloat(line.getAttribute("x1"));
        var y1 = parseFloat(line.getAttribute("y1"));
        var x2 = parseFloat(line.getAttribute("x2"));
        var y2 = parseFloat(line.getAttribute("y2"));
        label.setAttribute("x", (x1 + x2) / 2);
        label.setAttribute("y", (y1 + y2) / 2 - 6);
      }
    });
  }

  function attachNodePointerHandlers(g, node, svg, data, handlers) {
    if (!handlers.canEdit) return;

    var dragDisabled = !!handlers.connectMode;
    g.classList.add(dragDisabled ? "node-drag-disabled" : "node-draggable");
    if (dragDisabled) {
      if (handlers.onNodeSelect) {
        g.addEventListener("click", function (evt) {
          evt.stopPropagation();
          handlers.onNodeSelect(node);
        });
      }
      return;
    }

    var dragState = null;

    g.addEventListener("click", function (evt) {
      evt.stopPropagation();
    });

    function clearDragState(evt) {
      if (!dragState) return;
      try {
        g.releasePointerCapture(evt.pointerId);
      } catch (releaseErr) {
        /* pointer may already be released */
      }
      g.classList.remove("node-dragging");
      dragState = null;
    }

    function revertNodeVisual(savedX, savedY) {
      setNodeGroupPosition(g, savedX, savedY);
      updateEdgeEndpointsForNode(svg, node.id, savedX, savedY);
    }

    g.addEventListener("pointerdown", function (evt) {
      if (handlers.connectMode) return;
      if (evt.button !== 0) return;
      evt.stopPropagation();
      g.setPointerCapture(evt.pointerId);
      dragState = {
        pointerId: evt.pointerId,
        startPt: svgPoint(svg, evt),
        savedX: node.x,
        savedY: node.y,
        dragging: false,
      };
    });

    g.addEventListener("pointermove", function (evt) {
      if (!dragState || evt.pointerId !== dragState.pointerId) return;
      var curPt = svgPoint(svg, evt);
      var dx = curPt.x - dragState.startPt.x;
      var dy = curPt.y - dragState.startPt.y;
      if (!dragState.dragging) {
        if ((dx * dx + dy * dy) < (DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX)) return;
        dragState.dragging = true;
        g.classList.add("node-dragging");
        svg.appendChild(g);
      }
      evt.preventDefault();
      var bounds = getMapBounds(data);
      var clamped = clampNodePosition(
        dragState.savedX + dx,
        dragState.savedY + dy,
        bounds
      );
      setNodeGroupPosition(g, clamped.x, clamped.y);
      updateEdgeEndpointsForNode(svg, node.id, clamped.x, clamped.y);
    });

    function finishPointerInteraction(evt) {
      if (!dragState || evt.pointerId !== dragState.pointerId) return;
      if (dragState.dragging) {
        var bounds = getMapBounds(data);
        var curPt = svgPoint(svg, evt);
        var dx = curPt.x - dragState.startPt.x;
        var dy = curPt.y - dragState.startPt.y;
        var savedX = dragState.savedX;
        var savedY = dragState.savedY;
        var clamped = clampNodePosition(
          savedX + dx,
          savedY + dy,
          bounds
        );
        clearDragState(evt);
        if (handlers.onNodeDragComplete) {
          handlers.onNodeDragComplete(
            node,
            clamped.x,
            clamped.y,
            savedX,
            savedY,
            function () {
              revertNodeVisual(savedX, savedY);
            }
          );
        }
        return;
      }
      clearDragState(evt);
      if (handlers.onNodeSelect) handlers.onNodeSelect(node);
    }

    g.addEventListener("pointerup", finishPointerInteraction);
    g.addEventListener("pointercancel", function (evt) {
      if (!dragState || evt.pointerId !== dragState.pointerId) return;
      if (dragState.dragging) {
        revertNodeVisual(dragState.savedX, dragState.savedY);
      }
      clearDragState(evt);
    });
  }

  function renderGraph(svg, data, handlers) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var ns = "http://www.w3.org/2000/svg";
    var canEdit = handlers && handlers.canEdit;

    (data.edges || []).forEach(function (edge) {
      var from = data.nodes.find(function (n) { return n.id === edge.from_node_id; });
      var to = data.nodes.find(function (n) { return n.id === edge.to_node_id; });
      if (!from || !to) return;
      var line = document.createElementNS(ns, "line");
      line.setAttribute("x1", from.x);
      line.setAttribute("y1", from.y);
      line.setAttribute("x2", to.x);
      line.setAttribute("y2", to.y);
      line.setAttribute("class", edgeClass(edge));
      line.setAttribute("data-edge-id", edge.id);
      if (canEdit) {
        line.style.cursor = "pointer";
        line.addEventListener("click", function (evt) {
          evt.stopPropagation();
          if (handlers.onEdgeSelect) handlers.onEdgeSelect(edge);
        });
      }
      svg.appendChild(line);
      if (edge.label) {
        var midX = (from.x + to.x) / 2;
        var midY = (from.y + to.y) / 2;
        var label = document.createElementNS(ns, "text");
        label.setAttribute("x", midX);
        label.setAttribute("y", midY - 6);
        label.setAttribute("text-anchor", "middle");
        label.setAttribute("class", "edge-label");
        label.setAttribute("data-edge-id", edge.id);
        label.textContent = edge.label;
        svg.appendChild(label);
      }
    });

    (data.nodes || []).forEach(function (node) {
      var g = document.createElementNS(ns, "g");
      var nodeClass = "map-node node-type-" + node.node_type;
      if (node.is_optional) nodeClass += " node-optional";
      if (handlers.connectFrom === node.id) nodeClass += " node-connect-from";
      if (editorState.selectedNodeId === node.id) nodeClass += " node-selected";
      g.setAttribute("class", nodeClass);
      g.setAttribute("data-node-id", node.id);
      g.setAttribute("transform", "translate(" + node.x + "," + node.y + ")");
      g.setAttribute("tabindex", "0");
      g.setAttribute("role", "button");
      g.setAttribute("aria-label", (node.title || node.slug) + ", " + node.node_type);
      var circle = document.createElementNS(ns, "circle");
      circle.setAttribute("r", 24);
      circle.setAttribute("class", "node-circle");
      var icon = document.createElementNS(ns, "text");
      icon.setAttribute("class", "material-icons node-icon");
      icon.setAttribute("text-anchor", "middle");
      icon.setAttribute("dominant-baseline", "central");
      icon.setAttribute("y", "2");
      icon.textContent = resolveNodeIcon(node);
      var label = document.createElementNS(ns, "text");
      label.setAttribute("y", 40);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("class", "node-label");
      label.textContent = node.slug;
      g.appendChild(circle);
      g.appendChild(icon);
      g.appendChild(label);
      attachNodePointerHandlers(g, node, svg, data, handlers);
      svg.appendChild(g);
    });
  }

  function renderEdgeInspector(panel, edge, adventureId, onSaved) {
    if (!panel) return;
    var data = edge.condition_data || {};
    panel.innerHTML =
      "<h3 class=\"h6\">Edge #" + edge.id + "</h3>" +
      "<label class=\"form-label small\">Label</label>" +
      "<input type=\"text\" class=\"form-control form-control-sm mb-2\" id=\"edge-label\" value=\"" +
      (edge.label || "") + "\">" +
      "<label class=\"form-label small\">Condition type</label>" +
      "<select class=\"form-select form-select-sm mb-2\" id=\"edge-condition-type\">" +
      "<option value=\"always\"" + (edge.condition_type === "always" ? " selected" : "") + ">Always</option>" +
      "<option value=\"choice\"" + (edge.condition_type === "choice" ? " selected" : "") + ">Choice</option>" +
      "<option value=\"criteria\"" + (edge.condition_type === "criteria" ? " selected" : "") + ">Criteria</option>" +
      "</select>" +
      "<div id=\"edge-choice-fields\" class=\"mb-2" + (edge.condition_type === "choice" ? "" : " d-none") + "\">" +
      "<label class=\"form-label small\">Choice key</label>" +
      "<input type=\"text\" class=\"form-control form-control-sm\" id=\"edge-choice-key\" value=\"" +
      (data.choice_key || "") + "\">" +
      "</div>" +
      "<div id=\"edge-criteria-fields\" class=\"mb-2" + (edge.condition_type === "criteria" ? "" : " d-none") + "\">" +
      "<label class=\"form-label small\">Min score %</label>" +
      "<input type=\"number\" min=\"1\" max=\"100\" class=\"form-control form-control-sm mb-1\" id=\"edge-min-score\" value=\"" +
      (data.min_score_percent || "") + "\">" +
      "</div>" +
      "<label class=\"form-label small\">Unlock semantics</label>" +
      "<select class=\"form-select form-select-sm mb-2\" id=\"edge-unlock-semantics\">" +
      "<option value=\"and\"" + (edge.unlock_semantics === "and" ? " selected" : "") + ">AND</option>" +
      "<option value=\"or\"" + (edge.unlock_semantics === "or" ? " selected" : "") + ">OR</option>" +
      "</select>" +
      "<button type=\"button\" class=\"btn btn-primary btn-sm w-100 mb-2\" id=\"edge-save-btn\">Save edge</button>" +
      "<button type=\"button\" class=\"btn btn-outline-danger btn-sm w-100\" id=\"edge-delete-btn\">Delete edge</button>";

    document.getElementById("edge-condition-type").addEventListener("change", function (evt) {
      var val = evt.target.value;
      document.getElementById("edge-choice-fields").classList.toggle("d-none", val !== "choice");
      document.getElementById("edge-criteria-fields").classList.toggle("d-none", val !== "criteria");
    });

    document.getElementById("edge-save-btn").addEventListener("click", function () {
      var typeSelect = document.getElementById("edge-condition-type");
      var conditionType = typeSelect.value;
      var conditionData = {};
      if (conditionType === "choice") {
        conditionData.choice_key = document.getElementById("edge-choice-key").value.trim();
      } else if (conditionType === "criteria") {
        var minScore = document.getElementById("edge-min-score").value;
        if (minScore) conditionData.min_score_percent = parseInt(minScore, 10);
      }
      api("PATCH", "/teacher/adventures/" + adventureId + "/edges/" + edge.id, {
        label: document.getElementById("edge-label").value.trim() || null,
        condition_type: conditionType,
        condition_data: conditionData,
        unlock_semantics: document.getElementById("edge-unlock-semantics").value,
      }).then(function (body) {
        if (body.success) {
          if (body.data && body.data.edge) updateEdgeInState(body.data.edge);
          if (onSaved) onSaved(body.data.edge);
        } else {
          showEditorError(formatApiErrorMessage(body, "Could not save edge."));
        }
      });
    });

    document.getElementById("edge-delete-btn").addEventListener("click", function () {
      if (!confirm("Delete this connection?")) return;
      api("DELETE", "/teacher/adventures/" + adventureId + "/edges/" + edge.id).then(function (body) {
        if (body.success) {
          var snap = Object.assign({}, edge);
          recordCommand({
            label: "delete connection",
            undo: function () {
              return api("POST", "/teacher/adventures/" + adventureId + "/edges", {
                from_node_id: snap.from_node_id,
                to_node_id: snap.to_node_id,
                label: snap.label,
                condition_type: snap.condition_type,
                condition_data: snap.condition_data,
                unlock_semantics: snap.unlock_semantics,
              });
            },
            redo: function () {
              var current = (editorState.edges || []).find(function (e) {
                return e.from_node_id === snap.from_node_id && e.to_node_id === snap.to_node_id;
              });
              if (!current) return Promise.resolve({ success: true });
              return api("DELETE", "/teacher/adventures/" + adventureId + "/edges/" + current.id);
            },
          });
          removeEdgeFromState(edge.id);
          if (onSaved) onSaved(null);
        } else {
          showEditorError(formatApiErrorMessage(body, "Could not delete edge."));
        }
      });
    });
  }

  function renderQuizQuestionSetFields(node) {
    var sets = editorState.questionSets || [];
    var currentId = node.question_set_id;
    var inList = sets.some(function (qs) { return qs.id === currentId; });
    var html = "";
    if (sets.length === 0) {
      html +=
        "<p class=\"small text-muted mb-2\">No question sets yet. " +
        "<a href=\"/teacher/education/sets/create\">Create one</a> to attach quiz content.</p>";
    }
    if (currentId && !inList) {
      html +=
        "<div class=\"alert alert-warning py-1 px-2 small mb-2\" role=\"status\">" +
        "Question set unavailable (clone or pick your own).</div>";
    }
    html +=
      "<label class=\"form-label small\">Question set</label>" +
      "<select class=\"form-select form-select-sm mb-2\" id=\"node-question-set\">" +
      "<option value=\"\">— none —</option>";
    sets.forEach(function (qs) {
      var sel = currentId === qs.id ? " selected" : "";
      var count = qs.question_count != null ? qs.question_count : 0;
      html +=
        "<option value=\"" + qs.id + "\"" + sel + ">" +
        qs.title + " (" + count + " question" + (count === 1 ? "" : "s") + ")</option>";
    });
    html +=
      "</select>" +
      "<p class=\"small mb-2\"><a href=\"/teacher/education/sets\">Manage question sets</a></p>";
    return html;
  }

  function renderIconPicker(node) {
    var catalog = iconCatalog();
    var currentType = node.node_type;
    var stored = node.icon_url || "";
    var typeDefault = defaultIconFor(currentType);
    var selected = stored || typeDefault;
    var html = "<label class=\"form-label small\">Node icon</label>";
    html += "<p class=\"small text-muted mb-1\" id=\"icon-current-note\">";
    if (stored) {
      html += "Stored: <strong>" + stored + "</strong>";
      if (stored !== typeDefault) html += " · type default: " + typeDefault;
      if (catalog.every(function (i) { return i.ligature !== stored; }) && stored.charAt(0) !== "/") {
        html += " (not in library; map uses type default)";
      }
    } else {
      html += "Using type default: <strong>" + typeDefault + "</strong>";
    }
    html += "</p>";
    html += "<div class=\"node-icon-picker\" id=\"node-icon-picker\" role=\"listbox\" aria-label=\"Icon library\">";
    catalog.forEach(function (icon) {
      var isSel = icon.ligature === selected;
      html += "<button type=\"button\" class=\"node-icon-option" + (isSel ? " is-selected" : "") + "\" " +
        "data-ligature=\"" + icon.ligature + "\" title=\"" + icon.label + "\" role=\"option\" " +
        "aria-selected=\"" + (isSel ? "true" : "false") + "\">" +
        "<span class=\"material-icons\" aria-hidden=\"true\">" + icon.ligature + "</span></button>";
    });
    html += "</div>";
    html += "<button type=\"button\" class=\"btn btn-outline-secondary btn-sm w-100 mb-2\" id=\"node-icon-clear\">Clear override (use type default)</button>";
    html += "<input type=\"hidden\" id=\"node-icon-url\" value=\"" + (stored || "") + "\">";
    return html;
  }

  function renderNodeInspector(panel, node, adventureId, monsters, onSaved) {
    if (!panel) return;
    var monsterOptions = (monsters || []).map(function (m) {
      var sel = node.monster_id === m.id ? " selected" : "";
      return "<option value=\"" + m.id + "\"" + sel + ">" + m.name + "</option>";
    }).join("");
    var typeOptions = ALL_NODE_TYPES.map(function (t) {
      return "<option value=\"" + t + "\"" + (node.node_type === t ? " selected" : "") + ">" + t + "</option>";
    }).join("");
    panel.innerHTML =
      "<h3 class=\"h6\">Node: " + node.slug + "</h3>" +
      "<label class=\"form-label small\">Title</label>" +
      "<input type=\"text\" class=\"form-control form-control-sm mb-2\" id=\"node-title\" value=\"" +
      (node.title || "") + "\">" +
      "<label class=\"form-label small\">Type</label>" +
      "<select class=\"form-select form-select-sm mb-2\" id=\"node-type\">" + typeOptions + "</select>" +
      renderIconPicker(node) +
      (node.node_type === "battle"
        ? "<label class=\"form-label small\">Monster</label>" +
          "<select class=\"form-select form-select-sm mb-2\" id=\"node-monster\">" +
          "<option value=\"\">— pick monster —</option>" + monsterOptions + "</select>"
        : "") +
      (node.node_type === "quiz" ? renderQuizQuestionSetFields(node) : "") +
      "<button type=\"button\" class=\"btn btn-primary btn-sm w-100 mb-2\" id=\"node-save-btn\">Save node</button>" +
      "<button type=\"button\" class=\"btn btn-outline-danger btn-sm w-100\" id=\"node-delete-btn\">Delete node</button>";

    var iconHidden = document.getElementById("node-icon-url");
    document.querySelectorAll("#node-icon-picker .node-icon-option").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var lig = btn.getAttribute("data-ligature");
        if (iconHidden) iconHidden.value = lig;
        document.querySelectorAll("#node-icon-picker .node-icon-option").forEach(function (b) {
          b.classList.toggle("is-selected", b === btn);
          b.setAttribute("aria-selected", b === btn ? "true" : "false");
        });
      });
    });
    var clearBtn = document.getElementById("node-icon-clear");
    if (clearBtn) {
      clearBtn.addEventListener("click", function () {
        if (iconHidden) iconHidden.value = "";
        document.querySelectorAll("#node-icon-picker .node-icon-option").forEach(function (b) {
          b.classList.toggle("is-selected", b.getAttribute("data-ligature") === defaultIconFor(node.node_type));
        });
      });
    }
    var typeSelect = document.getElementById("node-type");
    if (typeSelect) {
      typeSelect.addEventListener("change", function () {
        var note = document.getElementById("icon-current-note");
        if (!note) return;
        var stored = iconHidden ? iconHidden.value : (node.icon_url || "");
        var typeDefault = defaultIconFor(typeSelect.value);
        if (stored) {
          note.innerHTML = "Stored: <strong>" + stored + "</strong> · new type default: " + typeDefault;
        } else {
          note.innerHTML = "Using type default: <strong>" + typeDefault + "</strong>";
        }
      });
    }

    document.getElementById("node-save-btn").addEventListener("click", function () {
      var payload = { title: document.getElementById("node-title").value.trim() };
      var typeEl = document.getElementById("node-type");
      if (typeEl && typeEl.value) {
        payload.node_type = typeEl.value;
        payload.is_start = typeEl.value === "start";
        payload.is_end = typeEl.value === "end";
      }
      var iconEl = document.getElementById("node-icon-url");
      if (iconEl) payload.icon_url = iconEl.value ? iconEl.value : null;
      var monsterEl = document.getElementById("node-monster");
      if (monsterEl && monsterEl.value) payload.monster_id = parseInt(monsterEl.value, 10);
      var questionSetEl = document.getElementById("node-question-set");
      if (questionSetEl) {
        payload.question_set_id = questionSetEl.value
          ? parseInt(questionSetEl.value, 10)
          : null;
      }
      api("PATCH", "/teacher/adventures/" + adventureId + "/nodes/" + node.id, payload).then(function (body) {
        if (body.success) {
          if (body.data && body.data.node) updateNodeInState(body.data.node);
          if (onSaved) onSaved(body.data.node);
          if (questionSetEl) showEditorSuccess("Node saved.");
        } else {
          showEditorError(formatApiErrorMessage(body, "Could not save node."));
        }
      });
    });

    document.getElementById("node-delete-btn").addEventListener("click", function () {
      if (!confirm("Delete node \"" + node.slug + "\" and its connections?")) return;
      var snapshot = Object.assign({}, node);
      var related = (editorState.edges || []).filter(function (e) {
        return e.from_node_id === node.id || e.to_node_id === node.id;
      }).map(function (e) { return Object.assign({}, e); });
      api("DELETE", "/teacher/adventures/" + adventureId + "/nodes/" + node.id).then(function (body) {
        if (body.success) {
          recordCommand({
            label: "delete node",
            undo: function () {
              return api("POST", "/teacher/adventures/" + adventureId + "/nodes", nodeRecreatePayload(snapshot)).then(function (undoBody) {
                if (!undoBody.success || !undoBody.data || !undoBody.data.node) return undoBody;
                var newId = undoBody.data.node.id;
                var chain = Promise.resolve();
                related.forEach(function (edge) {
                  chain = chain.then(function () {
                    return api("POST", "/teacher/adventures/" + adventureId + "/edges", {
                      from_node_id: edge.from_node_id === snapshot.id ? newId : edge.from_node_id,
                      to_node_id: edge.to_node_id === snapshot.id ? newId : edge.to_node_id,
                      label: edge.label,
                      condition_type: edge.condition_type,
                      condition_data: edge.condition_data,
                      unlock_semantics: edge.unlock_semantics,
                    });
                  });
                });
                return chain.then(function () { return undoBody; });
              });
            },
            redo: function () {
              var current = (editorState.nodes || []).find(function (n) { return n.slug === snapshot.slug; }) || snapshot;
              return api("DELETE", "/teacher/adventures/" + adventureId + "/nodes/" + current.id + "?confirm=true");
            },
          });
          removeNodeFromState(node.id);
          if (onSaved) onSaved(null);
          if (window.AdventureEditorCommands) {
            AdventureEditorCommands.announce("Node deleted.", "success");
          }
        } else {
          showEditorError(formatApiErrorMessage(body, "Could not delete node."));
        }
      });
    });
  }

  window.AdventureEditor = {
    initList: function (opts) {
      var currentUserId = (opts && opts.currentUserId) || null;
      var ownedList = document.getElementById("adventures-owned");
      var sharedList = document.getElementById("adventures-shared");
      var sharedHint = document.getElementById("shared-empty-hint");
      var btn = document.getElementById("btn-new-adventure");

      function renderItem(a, isShared) {
        var item = document.createElement("div");
        item.className = "list-group-item d-flex justify-content-between align-items-center";
        var meta = document.createElement("div");
        var titleLink = document.createElement("a");
        titleLink.href = "/teacher/adventures/" + a.id;
        titleLink.className = "fw-semibold text-decoration-none";
        titleLink.textContent = a.title;
        meta.appendChild(titleLink);
        var sub = document.createElement("div");
        sub.className = "small text-muted";
        var parts = [a.status];
        if (isShared && a.owner && a.owner.name) parts.unshift("by " + a.owner.name);
        if (a.is_public) parts.push("public");
        sub.textContent = parts.join(" · ");
        meta.appendChild(sub);
        item.appendChild(meta);
        if (isShared) {
          var cloneBtn = document.createElement("button");
          cloneBtn.type = "button";
          cloneBtn.className = "btn btn-outline-primary btn-sm";
          cloneBtn.textContent = "Clone";
          cloneBtn.addEventListener("click", function (evt) {
            evt.preventDefault();
            api("POST", "/teacher/adventures/" + a.id + "/clone", {}).then(function (body) {
              if (body.success && body.data.adventure) {
                window.location.href = "/teacher/adventures/" + body.data.adventure.id;
              }
            });
          });
          item.appendChild(cloneBtn);
        }
        return item;
      }

      function refresh() {
        api("GET", "/teacher/adventures/?format=json").then(function (body) {
          if (!body.success) return;
          var adventures = body.data.adventures || [];
          if (ownedList) ownedList.innerHTML = "";
          if (sharedList) sharedList.innerHTML = "";
          var owned = [];
          var shared = [];
          adventures.forEach(function (a) {
            if (currentUserId && a.owner && a.owner.id === currentUserId) owned.push(a);
            else shared.push(a);
          });
          owned.forEach(function (a) { if (ownedList) ownedList.appendChild(renderItem(a, false)); });
          if (!owned.length && ownedList) {
            var empty = document.createElement("p");
            empty.className = "text-muted small";
            empty.textContent = "No adventures yet. Create one to get started.";
            ownedList.appendChild(empty);
          }
          shared.forEach(function (a) { if (sharedList) sharedList.appendChild(renderItem(a, true)); });
          if (sharedHint) sharedHint.classList.toggle("d-none", shared.length > 0);
        });
      }

      if (btn) {
        btn.addEventListener("click", function () {
          api("POST", "/teacher/adventures/", { title: "New Adventure" }).then(function (body) {
            if (body.success && body.data.adventure) {
              window.location.href = "/teacher/adventures/" + body.data.adventure.id;
            }
          });
        });
      }
      refresh();
    },

    init: function (opts) {
      var adventureId = opts.adventureId;
      var canEdit = opts.canEdit !== false;
      var monsters = opts.monsters || [];
      editorState.adventureId = adventureId;
      editorState.canEdit = canEdit;
      editorState.monsters = monsters;
      editorState.questionSets = opts.questionSets || [];
      if (opts.adventureSettings) {
        editorState.adventure = Object.assign({}, opts.adventureSettings);
        applyCanvasBackground(opts.adventureSettings.background_image_url || null);
      }
      var svg = document.getElementById("adventure-canvas");
      var inspector = document.getElementById("map-inspector");
      var emptyHint = document.getElementById("canvas-empty-hint");
      var modeHint = document.getElementById("editor-mode-hint");
      var settingsModalEl = document.getElementById("adventure-settings-modal");
      var settingsBaseline = null;
      var pendingBackgroundFile = null;
      var pendingPreviewUrl = null;
      var activeNodeType = "start";
      var connectMode = false;
      var connectFrom = null;

      function hasStartNode() {
        return (editorState.nodes || []).some(function (n) {
          return n.node_type === "start" || !!n.is_start;
        });
      }

      function syncToolbarActive() {
        document.querySelectorAll("#node-toolbar [data-node-type]").forEach(function (b) {
          b.classList.toggle("active", !!activeNodeType && b.getAttribute("data-node-type") === activeNodeType);
        });
        var selectBtn = document.getElementById("btn-select-mode");
        if (selectBtn) {
          var selecting = !connectMode && !activeNodeType;
          selectBtn.classList.toggle("active", selecting);
          selectBtn.setAttribute("aria-pressed", selecting ? "true" : "false");
        }
        document.getElementById("btn-connect-mode")?.classList.toggle("active", connectMode);
      }

      function setModeHint() {
        if (!modeHint) return;
        if (connectMode) {
          modeHint.innerHTML = connectFrom
            ? "Now click the <strong>destination</strong> node."
            : "Click the <strong>first</strong> node, then the second.";
        } else if (!activeNodeType) {
          modeHint.innerHTML = "Click a node to select it. Pick a type to place another.";
        } else if (activeNodeType === "start" && hasStartNode()) {
          modeHint.innerHTML = "Click the map to place another <strong>Start</strong>. Students can begin at any start.";
        } else {
          modeHint.innerHTML = "Click the map to place a <strong>" + titleForType(activeNodeType) + "</strong> node.";
        }
      }

      function setPlacementTool(type) {
        var wasConnect = connectMode;
        connectMode = false;
        connectFrom = null;
        activeNodeType = type;
        syncToolbarActive();
        setModeHint();
        if (wasConnect) refreshGraph();
      }

      function enterSelectMode() {
        setPlacementTool(null);
      }

      function markSelectedNode(nodeId) {
        editorState.selectedNodeId = nodeId || null;
        if (!svg) return;
        svg.querySelectorAll(".map-node").forEach(function (el) {
          var id = parseInt(el.getAttribute("data-node-id"), 10);
          el.classList.toggle("node-selected", nodeId != null && id === nodeId);
        });
      }

      function updateEmptyHint() {
        if (!emptyHint) return;
        emptyHint.classList.toggle("d-none", editorState.nodes.length > 0);
      }

      function refreshGraph() {
        return loadGraph();
      }

      function bindShareToggle(adv) {
        var toggle = document.getElementById("toggle-is-public");
        if (!toggle || !canEdit) return;
        toggle.disabled = adv.status === "draft";
        toggle.checked = !!adv.is_public;
        toggle.onchange = function () {
          api("PATCH", "/teacher/adventures/" + adventureId, { is_public: toggle.checked }).then(function (body) {
            if (!body.success) {
              toggle.checked = !toggle.checked;
              showEditorError(formatApiErrorMessage(body, "Could not update sharing settings."));
            } else if (body.data.adventure) {
              updateAdventureInState(body.data.adventure);
              bindShareToggle(body.data.adventure);
              var settingsShare = document.getElementById("settings-is-public");
              if (settingsShare) settingsShare.checked = !!body.data.adventure.is_public;
            }
          });
        };
      }

      function updateHeaderTitle(title) {
        var el = document.getElementById("adventure-editor-title");
        if (el && title) el.textContent = title;
      }

      function updateSettingsBackgroundPreview(url) {
        var preview = document.getElementById("settings-background-preview");
        var wrap = document.getElementById("settings-background-preview-wrap");
        if (!preview) return;
        if (url) {
          preview.src = url;
          preview.classList.remove("d-none");
          if (wrap) wrap.classList.remove("d-none");
        } else {
          preview.removeAttribute("src");
          preview.classList.add("d-none");
          if (wrap) wrap.classList.add("d-none");
        }
      }

      function syncSettingsFormFromBaseline() {
        if (!settingsBaseline) return;
        var titleEl = document.getElementById("settings-title");
        var descEl = document.getElementById("settings-description");
        var themeEl = document.getElementById("settings-theme");
        var endEl = document.getElementById("settings-end-semantics");
        var shareEl = document.getElementById("settings-is-public");
        if (titleEl) titleEl.value = settingsBaseline.title || "";
        if (descEl) descEl.value = settingsBaseline.description || "";
        if (themeEl) themeEl.value = settingsBaseline.theme || "fantasy";
        if (endEl) endEl.value = settingsBaseline.end_semantics || "all";
        if (shareEl) {
          shareEl.checked = !!settingsBaseline.is_public;
          shareEl.disabled = settingsBaseline.status === "draft";
        }
        updateSettingsBackgroundPreview(settingsBaseline.background_image_url || null);
      }

      function captureSettingsBaselineFromState() {
        var adv = editorState.adventure || {};
        settingsBaseline = {
          title: adv.title || "",
          description: adv.description || "",
          theme: adv.theme || "fantasy",
          end_semantics: adv.end_semantics || "all",
          is_public: !!adv.is_public,
          background_image_url: adv.background_image_url || null,
          status: adv.status || "draft",
        };
        syncSettingsFormFromBaseline();
      }

      function collectSettingsFormValues() {
        return {
          title: (document.getElementById("settings-title") || {}).value.trim(),
          description: (document.getElementById("settings-description") || {}).value.trim(),
          theme: (document.getElementById("settings-theme") || {}).value,
          end_semantics: (document.getElementById("settings-end-semantics") || {}).value,
          is_public: !!(document.getElementById("settings-is-public") || {}).checked,
        };
      }

      function buildDirtySettingsPayload(baseline, current) {
        var payload = {};
        if (current.title !== baseline.title) payload.title = current.title;
        if (current.description !== baseline.description) payload.description = current.description;
        if (current.theme !== baseline.theme) payload.theme = current.theme;
        if (current.end_semantics !== baseline.end_semantics) payload.end_semantics = current.end_semantics;
        if (current.is_public !== baseline.is_public) payload.is_public = current.is_public;
        return payload;
      }

      function clearPendingBackgroundPreview() {
        if (pendingPreviewUrl) {
          URL.revokeObjectURL(pendingPreviewUrl);
          pendingPreviewUrl = null;
        }
        pendingBackgroundFile = null;
        var fileInput = document.getElementById("settings-background-file");
        if (fileInput) fileInput.value = "";
      }

      function initSettingsModal() {
        if (!settingsModalEl || typeof bootstrap === "undefined") return;
        var modal = bootstrap.Modal.getOrCreateInstance(settingsModalEl);

        settingsModalEl.addEventListener("show.bs.modal", function () {
          captureSettingsBaselineFromState();
          clearPendingBackgroundPreview();
        });

        var bgInput = document.getElementById("settings-background-file");
        if (bgInput) {
          bgInput.addEventListener("change", function (evt) {
            var file = evt.target.files && evt.target.files[0];
            if (!file) return;
            pendingBackgroundFile = file;
            if (pendingPreviewUrl) URL.revokeObjectURL(pendingPreviewUrl);
            pendingPreviewUrl = URL.createObjectURL(file);
            updateSettingsBackgroundPreview(pendingPreviewUrl);
          });
        }

        var saveBtn = document.getElementById("btn-settings-save");
        if (saveBtn) {
          saveBtn.addEventListener("click", function () {
            if (!settingsBaseline) captureSettingsBaselineFromState();
            var priorBackground = settingsBaseline.background_image_url || null;
            var hadBackgroundUpload = false;
            var uploadPromise = pendingBackgroundFile
              ? uploadBackgroundFile(adventureId, pendingBackgroundFile)
              : Promise.resolve({ success: true });

            uploadPromise.then(function (uploadBody) {
              if (pendingBackgroundFile && !uploadBody.success) {
                showEditorError(formatApiErrorMessage(uploadBody, "Could not upload background."));
                applyCanvasBackground(priorBackground);
                updateSettingsBackgroundPreview(priorBackground);
                return null;
              }
              if (pendingBackgroundFile && uploadBody.data && uploadBody.data.background_image_url) {
                hadBackgroundUpload = true;
                var uploadedUrl = uploadBody.data.background_image_url;
                applyCanvasBackground(uploadedUrl);
                settingsBaseline.background_image_url = uploadedUrl;
                updateAdventureInState({ background_image_url: uploadedUrl });
                clearPendingBackgroundPreview();
              }

              var current = collectSettingsFormValues();
              if (!current.title) {
                showEditorError("Title cannot be empty.");
                return null;
              }
              var payload = buildDirtySettingsPayload(settingsBaseline, current);
              if (!Object.keys(payload).length) {
                if (hadBackgroundUpload) {
                  showEditorSuccess("Settings saved.");
                  modal.hide();
                } else {
                  showEditorSuccess("No changes to save.");
                  modal.hide();
                }
                return null;
              }
              return api("PATCH", "/teacher/adventures/" + adventureId, payload);
            }).then(function (patchBody) {
              if (!patchBody) return;
              if (!patchBody.success) {
                showEditorError(formatApiErrorMessage(patchBody, "Could not save settings."));
                return;
              }
              if (patchBody.data && patchBody.data.adventure) {
                updateAdventureInState(patchBody.data.adventure);
                updateHeaderTitle(patchBody.data.adventure.title);
                bindShareToggle(patchBody.data.adventure);
                applyCanvasBackground(patchBody.data.adventure.background_image_url || null);
                settingsBaseline = {
                  title: patchBody.data.adventure.title || "",
                  description: patchBody.data.adventure.description || "",
                  theme: patchBody.data.adventure.theme || "fantasy",
                  end_semantics: patchBody.data.adventure.end_semantics || "all",
                  is_public: !!patchBody.data.adventure.is_public,
                  background_image_url: patchBody.data.adventure.background_image_url || null,
                  status: patchBody.data.adventure.status || settingsBaseline.status,
                };
              }
              showEditorSuccess("Settings saved.");
              modal.hide();
            });
          });
        }
      }

      document.getElementById("btn-clone-adventure")?.addEventListener("click", function () {
        api("POST", "/teacher/adventures/" + adventureId + "/clone", {}).then(function (body) {
          if (body.success && body.data.adventure) {
            window.location.href = "/teacher/adventures/" + body.data.adventure.id;
          }
        });
      });

      if (canEdit) {
        document.getElementById("btn-select-mode")?.addEventListener("click", function () {
          enterSelectMode();
        });

        document.querySelectorAll("#node-toolbar [data-node-type]").forEach(function (btn) {
          btn.addEventListener("click", function () {
            setPlacementTool(btn.getAttribute("data-node-type"));
          });
        });

        document.getElementById("btn-connect-mode")?.addEventListener("click", function () {
          if (connectMode) {
            enterSelectMode();
            return;
          }
          connectMode = true;
          connectFrom = null;
          activeNodeType = null;
          syncToolbarActive();
          setModeHint();
          refreshGraph();
        });

        svg?.addEventListener("click", function (evt) {
          if (connectMode) return;
          var target = evt.target;
          if (target && target.nodeType === 3) target = target.parentElement;
          if (target && target.closest && target.closest(".map-node")) return;
          if (!activeNodeType) {
            markSelectedNode(null);
            if (window.AdventureEditor.clearInspector) AdventureEditor.clearInspector();
            if (window.AdventureEditorCommands) AdventureEditorCommands.setSelection(null, null);
            return;
          }
          var pt = svgPoint(svg, evt);
          var slug = makeSlug(activeNodeType, editorState.nodes);
          var payload = {
            slug: slug,
            title: titleForType(activeNodeType),
            node_type: activeNodeType,
            x: Math.round(pt.x),
            y: Math.round(pt.y),
            is_start: activeNodeType === "start",
            is_end: activeNodeType === "end",
          };
          api("POST", "/teacher/adventures/" + adventureId + "/nodes", payload).then(function (body) {
            if (body.success) {
              var created = body.data && body.data.node;
              if (created) {
                recordCommand({
                  label: "place node",
                  undo: function () {
                    return api("DELETE", "/teacher/adventures/" + adventureId + "/nodes/" + created.id + "?confirm=true");
                  },
                  redo: function () {
                    return api("POST", "/teacher/adventures/" + adventureId + "/nodes", payload).then(function (redoBody) {
                      if (redoBody.success && redoBody.data && redoBody.data.node) {
                        created = redoBody.data.node;
                      }
                      return redoBody;
                    });
                  },
                });
              }
              if (created && (created.node_type === "start" || created.is_start)) {
                enterSelectMode();
              }
              refreshGraph().then(function () {
                if (created) handleNodeSelect(created);
              });
              if (window.AdventureEditorCommands) {
                AdventureEditorCommands.announce("Node placed.", "success");
              }
            } else {
              showEditorError(formatApiErrorMessage(body, "Could not add node."));
            }
          });
        });
      }

      function handleNodeDragComplete(node, x, y, savedX, savedY, revert) {
        api("PATCH", "/teacher/adventures/" + adventureId + "/nodes/" + node.id, {
          x: x,
          y: y,
        }).then(function (body) {
          if (body.success && body.data && body.data.node) {
            updateNodeInState(body.data.node);
            recordCommand({
              label: "move node",
              undo: function () {
                return api("PATCH", "/teacher/adventures/" + adventureId + "/nodes/" + node.id, {
                  x: savedX,
                  y: savedY,
                });
              },
              redo: function () {
                return api("PATCH", "/teacher/adventures/" + adventureId + "/nodes/" + node.id, {
                  x: x,
                  y: y,
                });
              },
            });
          } else {
            revert();
            showEditorError(formatApiErrorMessage(body, "Could not save node position."));
          }
        });
      }

      function handleNodeSelect(node) {
        if (connectMode) {
          if (!connectFrom) {
            connectFrom = node.id;
            setModeHint();
            refreshGraph();
            return;
          }
          if (connectFrom === node.id) return;
          api("POST", "/teacher/adventures/" + adventureId + "/edges", {
            from_node_id: connectFrom,
            to_node_id: node.id,
          }).then(function (body) {
            connectFrom = null;
            connectMode = false;
            document.getElementById("btn-connect-mode")?.classList.remove("active");
            setModeHint();
            if (body.success) {
              var createdEdge = body.data && body.data.edge;
              if (createdEdge) {
                recordCommand({
                  label: "connect nodes",
                  undo: function () {
                    return api("DELETE", "/teacher/adventures/" + adventureId + "/edges/" + createdEdge.id);
                  },
                  redo: function () {
                    return api("POST", "/teacher/adventures/" + adventureId + "/edges", {
                      from_node_id: createdEdge.from_node_id,
                      to_node_id: createdEdge.to_node_id,
                    }).then(function (redoBody) {
                      if (redoBody.success && redoBody.data && redoBody.data.edge) {
                        createdEdge = redoBody.data.edge;
                      }
                      return redoBody;
                    });
                  },
                });
              }
              refreshGraph();
              if (window.AdventureEditorCommands) {
                AdventureEditorCommands.announce("Nodes connected.", "success");
              }
            } else showEditorError(formatApiErrorMessage(body, "Could not create connection."));
          });
          return;
        }
        markSelectedNode(node.id);
        renderNodeInspector(inspector, node, adventureId, editorState.monsters, function (updated) {
          if (!updated) {
            markSelectedNode(null);
            if (window.AdventureEditor.clearInspector) AdventureEditor.clearInspector();
          }
          refreshGraph();
        });
        if (window.AdventureEditorCommands) {
          AdventureEditorCommands.setSelection(node.id, null);
        }
      }

      function loadGraph() {
        return api("GET", "/teacher/adventures/" + adventureId + "/graph").then(function (body) {
          if (!body.success) {
            showEditorError(formatApiErrorMessage(body, "Could not load adventure map."));
            return;
          }
          applyGraphPayload(body.data);
          updateEmptyHint();
          bindShareToggle(editorState.adventure);
          applyCanvasBackground(
            editorState.adventure && editorState.adventure.background_image_url
              ? editorState.adventure.background_image_url
              : null
          );
          renderGraph(svg, getGraphSnapshot(), {
            canEdit: canEdit,
            connectMode: connectMode,
            connectFrom: connectFrom,
            onNodeSelect: canEdit ? handleNodeSelect : null,
            onNodeDragComplete: canEdit ? handleNodeDragComplete : null,
            onEdgeSelect: canEdit ? function (edge) {
              if (window.AdventureEditorCommands) {
                AdventureEditorCommands.setSelection(null, edge.id);
              }
              renderEdgeInspector(inspector, edge, adventureId, function () {
                refreshGraph();
              });
            } : null,
          });
          updatePublishValidationBanner(body.data.validation);
        });
      }

      document.getElementById("btn-save-graph")?.addEventListener("click", refreshGraph);
      document.getElementById("btn-publish")?.addEventListener("click", function () {
        api("POST", "/teacher/adventures/" + adventureId + "/publish").then(function (body) {
          if (body.success) {
            showEditorSuccess("Adventure published.");
            refreshGraph();
          } else {
            showEditorError(formatApiErrorMessage(body, "Could not publish adventure."));
          }
        });
      });

      setModeHint();
      if (canEdit) initSettingsModal();
      if (window.AdventureEditorCommands && AdventureEditorCommands.init) {
        AdventureEditorCommands.init({
          canEdit: canEdit,
          adventureId: adventureId,
          api: api,
        });
      }
      window.AdventureEditor.refreshGraph = refreshGraph;
      window.AdventureEditor.inspectNode = function (node) {
        handleNodeSelect(node);
      };
      window.AdventureEditor.clearInspector = function () {
        markSelectedNode(null);
        if (!inspector) return;
        inspector.innerHTML = canEdit
          ? "<p class=\"text-muted small mb-0\">Click a node to edit it, or an edge to edit path rules.</p>"
          : "<p class=\"text-muted small mb-0\">View-only preview.</p>";
      };
      window.AdventureEditor.deleteSelectedNode = function (node) {
        if (!node) return;
        var snapshot = Object.assign({}, node);
        api("DELETE", "/teacher/adventures/" + adventureId + "/nodes/" + node.id).then(function (body) {
          if (body.success) {
            recordCommand({
              label: "delete node",
              undo: function () {
                return api("POST", "/teacher/adventures/" + adventureId + "/nodes", nodeRecreatePayload(snapshot));
              },
              redo: function () {
                var current = (editorState.nodes || []).find(function (n) { return n.slug === snapshot.slug; });
                if (!current) return Promise.resolve({ success: true });
                return api("DELETE", "/teacher/adventures/" + adventureId + "/nodes/" + current.id + "?confirm=true");
              },
            });
            removeNodeFromState(node.id);
            markSelectedNode(null);
            if (window.AdventureEditor.clearInspector) AdventureEditor.clearInspector();
            refreshGraph();
          } else {
            showEditorError(formatApiErrorMessage(body, "Could not delete node."));
          }
        });
      };
      window.AdventureEditor.deleteSelectedEdge = function (edge) {
        if (!edge) return;
        api("DELETE", "/teacher/adventures/" + adventureId + "/edges/" + edge.id).then(function (body) {
          if (body.success) refreshGraph();
          else showEditorError(formatApiErrorMessage(body, "Could not delete edge."));
        });
      };
      loadGraph().then(function () {
        if (canEdit && hasStartNode()) enterSelectMode();
      });
    },

    getState: function () {
      return editorState;
    },
  };
})();
