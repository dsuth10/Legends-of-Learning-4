/**
 * Student Adventures map player.
 *
 * Accessibility: unlocked/available nodes are focusable; Enter/Space opens the detail panel.
 */
(function () {
  "use strict";

  async function api(method, url, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    return res.json();
  }

  function statusClass(status) {
    return "node-status-" + (status || "locked");
  }

  function edgeClass(edge, progressByNode) {
    var cls = "edge-line";
    var fromProg = progressByNode[edge.from_node_id];
    if (edge.condition_type === "choice") cls += " edge-choice";
    if (fromProg && fromProg.status === "completed" && edge.condition_type === "choice") {
      var key = (edge.condition_data || {}).choice_key;
      if (fromProg.choice_made && key && fromProg.choice_made !== key) {
        cls += " edge-locked-branch";
      } else if (fromProg.choice_made === key) {
        cls += " edge-active-branch";
      }
    }
    return cls;
  }

  function renderMap(svg, state) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var ns = "http://www.w3.org/2000/svg";
    var progressByNode = {};
    (state.my_progress.nodes || []).forEach(function (p) {
      progressByNode[p.node_id] = p;
    });

    (state.edges || []).forEach(function (edge) {
      var from = state.nodes.find(function (n) { return n.id === edge.from_node_id; });
      var to = state.nodes.find(function (n) { return n.id === edge.to_node_id; });
      if (!from || !to) return;
      var line = document.createElementNS(ns, "line");
      line.setAttribute("x1", from.x);
      line.setAttribute("y1", from.y);
      line.setAttribute("x2", to.x);
      line.setAttribute("y2", to.y);
      line.setAttribute("class", edgeClass(edge, progressByNode));
      svg.appendChild(line);
    });

    (state.nodes || []).forEach(function (node) {
      var prog = progressByNode[node.id] || { status: "locked" };
      var g = document.createElementNS(ns, "g");
      var cls = "map-node " + statusClass(prog.status);
      if (node.is_optional) cls += " node-optional";
      g.setAttribute("class", cls);
      g.setAttribute("data-slug", node.slug);
      g.setAttribute("role", "button");
      var focusable = prog.status === "available" || prog.status === "in_progress" || prog.status === "completed";
      g.setAttribute("tabindex", focusable ? "0" : "-1");
      g.setAttribute("aria-label", node.title + ", status " + prog.status);
      g.setAttribute("transform", "translate(" + node.x + "," + node.y + ")");
      var circle = document.createElementNS(ns, "circle");
      circle.setAttribute("r", 28);
      var label = document.createElementNS(ns, "text");
      label.setAttribute("y", 44);
      label.setAttribute("text-anchor", "middle");
      label.textContent = node.title;
      g.appendChild(circle);
      g.appendChild(label);
      g.addEventListener("click", function () {
        window.AdventurePlayer.showNode(node.slug);
      });
      g.addEventListener("keydown", function (evt) {
        if (evt.key === "Enter" || evt.key === " ") {
          evt.preventDefault();
          window.AdventurePlayer.showNode(node.slug);
        }
      });
      svg.appendChild(g);
    });
  }

  function renderDetail(panel, detail, adventureId) {
    var node = detail.node;
    var status = node.my_progress.status;
    var html = "<h2 class=\"text-lg font-bold\">" + node.title + "</h2>";
    html += "<p class=\"text-sm text-gray-400 mt-1\">" + (node.description || "") + "</p>";
    html += "<p class=\"text-xs mt-2\">Status: <span class=\"" + statusClass(status) + "\">" + status + "</span></p>";

    if (node.node_type === "choice" && detail.outgoing_choices && detail.outgoing_choices.length) {
      html += "<div class=\"choice-options mt-3\">";
      if (status === "completed" && node.my_progress.choice_made) {
        html += "<p class=\"text-sm choice-selected\">You chose: <strong>" +
          node.my_progress.choice_made + "</strong></p>";
      } else if (status === "available" || status === "in_progress") {
        detail.outgoing_choices.forEach(function (choice) {
          html += "<button type=\"button\" class=\"choice-btn mt-2 w-full py-2 rounded\" " +
            "data-choice-key=\"" + choice.choice_key + "\">" +
            (choice.label || choice.choice_key) + "</button>";
        });
      }
      html += "</div>";
    } else if (status === "available" || status === "in_progress") {
      html += "<button type=\"button\" class=\"mt-4 w-full py-2 bg-indigo-600 rounded\" id=\"btn-node-action\">";
      html += status === "in_progress" &&
        ["story", "reward", "milestone", "end", "start"].indexOf(node.node_type) >= 0
        ? "Complete" : "Start";
      html += "</button>";
    }

    panel.innerHTML = html;

    panel.querySelectorAll(".choice-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var key = btn.getAttribute("data-choice-key");
        api("POST", "/student/adventures/" + adventureId + "/nodes/" + node.slug + "/start")
          .then(function () {
            return api(
              "POST",
              "/student/adventures/" + adventureId + "/nodes/" + node.slug + "/choose",
              { choice_key: key }
            );
          })
          .then(function (body) {
            if (body.success) window.AdventurePlayer.refresh();
          });
      });
    });

    var actionBtn = document.getElementById("btn-node-action");
    if (!actionBtn) return;
    actionBtn.addEventListener("click", function () {
      var action = status === "in_progress" ? "complete" : "start";
      api("POST", "/student/adventures/" + adventureId + "/nodes/" + node.slug + "/" + action)
        .then(function (body) {
          if (body.success) {
            if (body.data.redirect_url) window.location.href = body.data.redirect_url;
            window.AdventurePlayer.refresh();
          }
        });
    });
  }

  window.AdventurePlayer = {
    _adventureId: null,
    _state: null,

    init: function (opts) {
      this._adventureId = opts.adventureId;
      this.refresh();
    },

    refresh: function () {
      var self = this;
      var svg = document.getElementById("adventure-map");
      api("GET", "/student/adventures/" + this._adventureId + "/state").then(function (body) {
        if (!body.success) return;
        self._state = body.data;
        if (svg) {
          svg.setAttribute("width", body.data.adventure.width);
          svg.setAttribute("height", body.data.adventure.height);
          renderMap(svg, body.data);
        }
      });
    },

    showNode: function (slug) {
      var self = this;
      var panel = document.getElementById("node-detail-panel");
      api("GET", "/student/adventures/" + this._adventureId + "/nodes/" + slug).then(function (body) {
        if (body.success && panel) renderDetail(panel, body.data, self._adventureId);
      });
    },
  };
})();
