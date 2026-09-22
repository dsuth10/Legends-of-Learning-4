/**
 * Student Adventures map player.
 *
 * Accessibility: unlocked/available nodes are focusable; Enter/Space opens the detail panel.
 * Locked nodes are not activatable. Travel and mini-map live in adventure_player_map.js.
 */
(function () {
  "use strict";

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
  var DEFAULT_IMAGES = {
    start: "node_start", story: "node_story", battle: "node_battle", quiz: "node_quiz",
    choice: "node_choice", reward: "node_treasure", milestone: "node_milestone",
    boss: "node_boss", end: "node_end",
  };

  async function api(method, url, body) {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    return res.json();
  }

  function statusClass(status) {
    return "node-status-" + (status || "locked");
  }

  function isImageIcon(value) {
    return !!value && /^\/static\/.+\.(png|jpe?g|webp|svg)(?:[?#].*)?$/i.test(value);
  }

  function iconLigature(node) {
    var value = node.icon_url;
    if (isImageIcon(value)) return value;
    if (value && !/^(https?:|data:|\/\/)/i.test(value) && !/\.(png|jpe?g|webp|svg)(?:[?#].*)?$/i.test(value)) return value;
    if (value) return DEFAULT_ICONS[node.node_type] || "flag";
    return "/static/images/adventure_node_icons/" + (DEFAULT_IMAGES[node.node_type] || "node_start") + ".png";
  }

  function appendNodeIcon(g, value, ns, radius, fallbackLigature) {
    if (isImageIcon(value)) {
      var image = document.createElementNS(ns, "image");
      image.setAttribute("class", "node-icon-image");
      image.setAttribute("x", -radius * 0.58);
      image.setAttribute("y", -radius * 0.58);
      image.setAttribute("width", radius * 1.16);
      image.setAttribute("height", radius * 1.16);
      image.setAttribute("preserveAspectRatio", "xMidYMid meet");
      image.setAttribute("href", value);
      image.addEventListener("error", function () {
        var fallback = document.createElementNS(ns, "text");
        fallback.setAttribute("class", "material-icons node-icon");
        fallback.setAttribute("text-anchor", "middle");
        fallback.setAttribute("dominant-baseline", "central");
        fallback.setAttribute("y", "2");
        fallback.textContent = fallbackLigature || "flag";
        g.replaceChild(fallback, image);
      });
      g.appendChild(image);
      return;
    }
    var icon = document.createElementNS(ns, "text");
    icon.setAttribute("class", "material-icons node-icon");
    icon.setAttribute("text-anchor", "middle");
    icon.setAttribute("dominant-baseline", "central");
    icon.setAttribute("y", "2");
    icon.textContent = value || "flag";
    g.appendChild(icon);
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

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char];
    });
  }

  function renderRewardPreview(rewards) {
    if (!Array.isArray(rewards) || !rewards.length) return "";
    var icons = {
      experience: "reward_xp.png",
      clan_experience: "reward_xp.png",
      gold: "reward_gold.png",
      special_currency: "reward_gold.png",
      equipment: "reward_item.png",
      ability: "reward_item.png",
      badge: "reward_item.png",
    };
    var labels = {
      experience: "XP",
      clan_experience: "clan XP",
      gold: "gold",
      special_currency: "special currency",
      equipment: "Equipment reward",
      ability: "Ability reward",
      badge: "Badge reward",
    };
    var html = "<section class=\"adventure-rewards mt-3\" aria-label=\"Possible rewards\">" +
      "<h3 class=\"adventure-rewards-heading\">Possible rewards</h3>";
    rewards.forEach(function (reward) {
      if (!reward) return;
      var type = reward.type || "";
      var label = labels[type];
      if (!label) return;
      var amount = Number(reward.amount);
      var validAmount = Number.isFinite(amount) && amount > 0;
      var text = label;
      if (["experience", "clan_experience", "gold", "special_currency"].indexOf(type) >= 0) {
        text = (validAmount ? "+" + amount.toLocaleString("en-AU") + " " : "") + label;
      } else if (type === "badge" && reward.badge_name) {
        text = "Badge: " + reward.badge_name;
      } else if (validAmount && amount > 1) {
        text += " (" + amount.toLocaleString("en-AU") + ")";
      }
      var condition = reward.condition_summary ?
        "<span class=\"adventure-reward-condition\">" + escapeHtml(reward.condition_summary) + "</span>" : "";
      html += "<div class=\"adventure-reward-chip\">" +
        "<img src=\"/static/images/quests/" + icons[type] + "\" alt=\"\" aria-hidden=\"true\">" +
        "<span class=\"adventure-reward-label\">" + escapeHtml(text) + "</span>" + condition + "</div>";
    });
    return html + "</section>";
  }

  function renderMap(svg, state) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    var ns = "http://www.w3.org/2000/svg";
    var progressByNode = {};
    (state.my_progress.nodes || []).forEach(function (p) {
      progressByNode[p.node_id] = p;
    });

    var backgroundUrl = state.adventure && state.adventure.background_image_url;
    if (backgroundUrl && /^\/static\//.test(backgroundUrl)) {
      var background = document.createElementNS(ns, "image");
      background.setAttribute("class", "adventure-map-background");
      background.setAttribute("x", "0");
      background.setAttribute("y", "0");
      background.setAttribute("width", state.adventure.width);
      background.setAttribute("height", state.adventure.height);
      background.setAttribute("preserveAspectRatio", "xMidYMid slice");
      background.setAttribute("href", backgroundUrl);
      background.setAttribute("aria-hidden", "true");
      svg.appendChild(background);
    }

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
      g.setAttribute("data-node-id", node.id);
      g.setAttribute("transform", "translate(" + node.x + "," + node.y + ")");
      var focusable = prog.status === "available" || prog.status === "in_progress" || prog.status === "completed";
      g.setAttribute("aria-label", node.title + ", " + node.node_type + ", " + prog.status);
      if (focusable) {
        g.setAttribute("role", "button");
        g.setAttribute("tabindex", "0");
        g.addEventListener("click", function () {
          if (window.AdventurePlayerMap && AdventurePlayerMap.interrupt) {
            AdventurePlayerMap.interrupt();
          }
          window.AdventurePlayer.showNode(node.slug);
        });
        g.addEventListener("keydown", function (evt) {
          if (evt.key === "Enter" || evt.key === " ") {
            evt.preventDefault();
            if (window.AdventurePlayerMap && AdventurePlayerMap.interrupt) {
              AdventurePlayerMap.interrupt();
            }
            window.AdventurePlayer.showNode(node.slug);
          }
        });
      } else {
        g.setAttribute("tabindex", "-1");
        g.setAttribute("aria-disabled", "true");
      }
      var circle = document.createElementNS(ns, "circle");
      circle.setAttribute("r", 28);
      var label = document.createElementNS(ns, "text");
      label.setAttribute("y", 44);
      label.setAttribute("text-anchor", "middle");
      label.textContent = node.title;
      g.appendChild(circle);
      appendNodeIcon(g, iconLigature(node), ns, 28, DEFAULT_ICONS[node.node_type]);
      var overlayName = prog.status === "completed" ? "node_complete" :
        (prog.status === "in_progress" ? "node_current" :
          (prog.status === "locked" ? "node_locked" : null));
      if (overlayName) {
        var overlay = document.createElementNS(ns, "image");
        overlay.setAttribute("class", "node-status-image");
        overlay.setAttribute("x", 12);
        overlay.setAttribute("y", -27);
        overlay.setAttribute("width", 18);
        overlay.setAttribute("height", 18);
        overlay.setAttribute("href", "/static/images/adventure_node_icons/" + overlayName + ".png");
        overlay.setAttribute("aria-hidden", "true");
        g.appendChild(overlay);
      }
      g.appendChild(label);
      svg.appendChild(g);
    });
  }

  function renderDetail(panel, detail, adventureId) {
    var node = detail.node;
    var status = node.my_progress.status;
    var html = "<h2 class=\"text-lg font-bold\">" + node.title + "</h2>";
    html += "<p class=\"text-sm text-gray-400 mt-1\">" + (node.description || "") + "</p>";
    html += "<p class=\"text-xs mt-2\">Status: <span class=\"" + statusClass(status) + "\">" + status + "</span></p>";
    html += renderRewardPreview(node.rewards_preview);

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
    panel.querySelectorAll(".adventure-reward-chip img").forEach(function (image) {
      image.addEventListener("error", function () { image.remove(); });
    });
    panel.setAttribute("tabindex", "-1");
    panel.focus();

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
            if (body.success) {
              window.AdventurePlayer.refresh({
                fromNodeId: node.id,
                nextUnlocked: (body.data && body.data.next_unlocked) || [],
              });
            }
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
            if (body.data && body.data.redirect_url) {
              window.location.href = body.data.redirect_url;
              return;
            }
            var travel = action === "complete"
              ? {
                fromNodeId: node.id,
                nextUnlocked: (body.data && body.data.next_unlocked) || [],
              }
              : null;
            window.AdventurePlayer.refresh(travel);
          }
        });
    });
  }

  window.AdventurePlayer = {
    _adventureId: null,
    _state: null,

    init: function (opts) {
      this._adventureId = opts.adventureId;
      if (window.AdventurePlayerMap && AdventurePlayerMap.init) {
        AdventurePlayerMap.init({ adventureId: this._adventureId });
      }
      document.addEventListener("keydown", function (evt) {
        if (evt.key !== "Escape") return;
        var panel = document.getElementById("node-detail-panel");
        if (!panel || !panel.contains(document.activeElement)) return;
        evt.preventDefault();
        var svg = document.getElementById("adventure-map");
        if (svg) svg.focus();
      });
      this.refresh();
    },

    refresh: function (travelOpts) {
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
        if (window.AdventurePlayerMap && AdventurePlayerMap.refresh) {
          AdventurePlayerMap.refresh(body.data, travelOpts || null);
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
