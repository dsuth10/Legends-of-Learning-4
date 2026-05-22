/**
 * Teacher Adventures map editor (vanilla JS + SVG).
 */
(function () {
  "use strict";

  var NODE_TYPES = ["start", "story", "battle", "quiz", "choice", "end"];

  async function api(method, url, body) {
    var opts = { method: method, headers: { "Content-Type": "application/json" } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    var res = await fetch(url, opts);
    return res.json();
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
        label.textContent = edge.label;
        svg.appendChild(label);
      }
    });

    (data.nodes || []).forEach(function (node) {
      var g = document.createElementNS(ns, "g");
      var nodeClass = "map-node node-type-" + node.node_type;
      if (node.is_optional) nodeClass += " node-optional";
      if (handlers.connectFrom === node.id) nodeClass += " node-connect-from";
      g.setAttribute("class", nodeClass);
      g.setAttribute("data-node-id", node.id);
      g.setAttribute("transform", "translate(" + node.x + "," + node.y + ")");
      var circle = document.createElementNS(ns, "circle");
      circle.setAttribute("r", 24);
      circle.setAttribute("class", "node-circle");
      var label = document.createElementNS(ns, "text");
      label.setAttribute("y", 40);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("class", "node-label");
      label.textContent = node.slug;
      g.appendChild(circle);
      g.appendChild(label);
      if (canEdit) {
        g.style.cursor = "pointer";
        g.addEventListener("click", function (evt) {
          evt.stopPropagation();
          if (handlers.onNodeSelect) handlers.onNodeSelect(node);
        });
      }
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
        if (body.success && onSaved) onSaved(body.data.edge);
      });
    });

    document.getElementById("edge-delete-btn").addEventListener("click", function () {
      if (!confirm("Delete this connection?")) return;
      api("DELETE", "/teacher/adventures/" + adventureId + "/edges/" + edge.id).then(function (body) {
        if (body.success && onSaved) onSaved(null);
      });
    });
  }

  function renderNodeInspector(panel, node, adventureId, monsters, onSaved) {
    if (!panel) return;
    var monsterOptions = (monsters || []).map(function (m) {
      var sel = node.monster_id === m.id ? " selected" : "";
      return "<option value=\"" + m.id + "\"" + sel + ">" + m.name + "</option>";
    }).join("");
    panel.innerHTML =
      "<h3 class=\"h6\">Node: " + node.slug + "</h3>" +
      "<label class=\"form-label small\">Title</label>" +
      "<input type=\"text\" class=\"form-control form-control-sm mb-2\" id=\"node-title\" value=\"" +
      (node.title || "") + "\">" +
      "<p class=\"small text-muted mb-2\">Type: <strong>" + node.node_type + "</strong></p>" +
      (node.node_type === "battle"
        ? "<label class=\"form-label small\">Monster</label>" +
          "<select class=\"form-select form-select-sm mb-2\" id=\"node-monster\">" +
          "<option value=\"\">— pick monster —</option>" + monsterOptions + "</select>"
        : "") +
      "<button type=\"button\" class=\"btn btn-primary btn-sm w-100 mb-2\" id=\"node-save-btn\">Save node</button>" +
      "<button type=\"button\" class=\"btn btn-outline-danger btn-sm w-100\" id=\"node-delete-btn\">Delete node</button>";

    document.getElementById("node-save-btn").addEventListener("click", function () {
      var payload = { title: document.getElementById("node-title").value.trim() };
      var monsterEl = document.getElementById("node-monster");
      if (monsterEl && monsterEl.value) payload.monster_id = parseInt(monsterEl.value, 10);
      api("PATCH", "/teacher/adventures/" + adventureId + "/nodes/" + node.id, payload).then(function (body) {
        if (body.success && onSaved) onSaved(body.data.node);
      });
    });

    document.getElementById("node-delete-btn").addEventListener("click", function () {
      if (!confirm("Delete node \"" + node.slug + "\" and its connections?")) return;
      api("DELETE", "/teacher/adventures/" + adventureId + "/nodes/" + node.id).then(function (body) {
        if (body.success && onSaved) onSaved(null);
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
      var svg = document.getElementById("adventure-canvas");
      var validationEl = document.getElementById("editor-validation");
      var inspector = document.getElementById("map-inspector");
      var emptyHint = document.getElementById("canvas-empty-hint");
      var modeHint = document.getElementById("editor-mode-hint");
      var graphData = null;
      var activeNodeType = "start";
      var connectMode = false;
      var connectFrom = null;

      function setModeHint() {
        if (!modeHint) return;
        if (connectMode) {
          modeHint.innerHTML = connectFrom
            ? "Now click the <strong>destination</strong> node."
            : "Click the <strong>first</strong> node, then the second.";
        } else {
          modeHint.innerHTML = "Click the map to place a <strong>" + titleForType(activeNodeType) + "</strong> node.";
        }
      }

      function updateEmptyHint() {
        if (!emptyHint || !graphData) return;
        emptyHint.classList.toggle("d-none", (graphData.nodes || []).length > 0);
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
            } else if (body.data.adventure) {
              bindShareToggle(body.data.adventure);
            }
          });
        };
      }

      document.getElementById("btn-clone-adventure")?.addEventListener("click", function () {
        api("POST", "/teacher/adventures/" + adventureId + "/clone", {}).then(function (body) {
          if (body.success && body.data.adventure) {
            window.location.href = "/teacher/adventures/" + body.data.adventure.id;
          }
        });
      });

      if (canEdit) {
        document.querySelectorAll("#node-toolbar [data-node-type]").forEach(function (btn) {
          btn.addEventListener("click", function () {
            connectMode = false;
            connectFrom = null;
            document.getElementById("btn-connect-mode")?.classList.remove("active");
            document.querySelectorAll("#node-toolbar [data-node-type]").forEach(function (b) {
              b.classList.toggle("active", b === btn);
            });
            activeNodeType = btn.getAttribute("data-node-type");
            setModeHint();
            refreshGraph();
          });
        });

        document.getElementById("btn-connect-mode")?.addEventListener("click", function () {
          connectMode = !connectMode;
          connectFrom = null;
          this.classList.toggle("active", connectMode);
          setModeHint();
          refreshGraph();
        });

        svg?.addEventListener("click", function (evt) {
          if (!connectMode) {
            var pt = svgPoint(svg, evt);
            var slug = makeSlug(activeNodeType, graphData ? graphData.nodes : []);
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
              if (body.success) refreshGraph();
              else if (validationEl) {
                validationEl.classList.remove("d-none");
                validationEl.textContent = body.message || "Could not add node.";
              }
            });
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
            if (body.success) refreshGraph();
          });
          return;
        }
        renderNodeInspector(inspector, node, adventureId, monsters, function () {
          refreshGraph();
        });
      }

      function loadGraph() {
        return api("GET", "/teacher/adventures/" + adventureId + "/graph").then(function (body) {
          if (!body.success) return;
          graphData = body.data;
          updateEmptyHint();
          bindShareToggle(graphData.adventure);
          renderGraph(svg, graphData, {
            canEdit: canEdit,
            connectFrom: connectFrom,
            onNodeSelect: canEdit ? handleNodeSelect : null,
            onEdgeSelect: canEdit ? function (edge) {
              renderEdgeInspector(inspector, edge, adventureId, function () {
                refreshGraph();
              });
            } : null,
          });
          if (validationEl && graphData.validation) {
            var hasErrors = !graphData.validation.ok_to_publish;
            validationEl.classList.toggle("d-none", !hasErrors);
            validationEl.textContent = hasErrors
              ? "Before publishing: " + graphData.validation.errors.map(function (e) { return e.message; }).join(" ")
              : "";
          }
        });
      }

      document.getElementById("btn-save-graph")?.addEventListener("click", refreshGraph);
      document.getElementById("btn-publish")?.addEventListener("click", function () {
        api("POST", "/teacher/adventures/" + adventureId + "/publish").then(function (body) {
          if (body.success) refreshGraph();
          else if (validationEl) {
            validationEl.classList.remove("d-none");
            validationEl.textContent = (body.errors || []).map(function (e) { return e.message; }).join(" ");
          }
        });
      });

      setModeHint();
      loadGraph();
    },
  };
})();
