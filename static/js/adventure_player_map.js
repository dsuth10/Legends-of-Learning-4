/**
 * Student map overlay: character marker, travel, and mini-map.
 */
(function () {
  "use strict";

  var NS = "http://www.w3.org/2000/svg";
  var TRAVEL_MS = 1200;
  var MARKER_ID = "character-marker";

  var mapState = {
    adventureId: null,
    svg: null,
    container: null,
    live: null,
    overview: null,
    overviewSvg: null,
    state: null,
    markerPos: null,
    animFrame: null,
    copies: [],
    pendingFinal: null,
  };

  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function announce(message) {
    if (!mapState.live || !message) return;
    mapState.live.textContent = "";
    window.setTimeout(function () {
      if (mapState.live) mapState.live.textContent = message;
    }, 20);
  }

  function nodeById(id) {
    var nodes = (mapState.state && mapState.state.nodes) || [];
    return nodes.find(function (n) { return n.id === id; }) || null;
  }

  function progressByNode() {
    var map = {};
    var rows = (mapState.state && mapState.state.my_progress && mapState.state.my_progress.nodes) || [];
    rows.forEach(function (p) { map[p.node_id] = p; });
    return map;
  }

  function markerOrigin() {
    var state = mapState.state;
    if (!state) return null;
    var currentId = state.my_progress && state.my_progress.current_node_id;
    if (currentId && nodeById(currentId)) return nodeById(currentId);
    var rows = (state.my_progress && state.my_progress.nodes) || [];
    var latest = null;
    rows.forEach(function (p) {
      if (p.status !== "completed") return;
      if (!latest || (p.completed_at && latest.completed_at && p.completed_at > latest.completed_at) || (!latest.completed_at && p.completed_at)) {
        latest = p;
      }
    });
    if (latest && nodeById(latest.node_id)) return nodeById(latest.node_id);
    return (state.nodes || []).find(function (n) {
      var p = progressByNode()[n.id];
      return n.is_start && p && p.status === "available";
    }) || (state.nodes || [])[0] || null;
  }

  function ensureMarker(x, y) {
    var svg = mapState.svg;
    if (!svg) return null;
    var g = svg.querySelector("#" + MARKER_ID);
    if (!g) {
      g = document.createElementNS(NS, "g");
      g.setAttribute("id", MARKER_ID);
      g.setAttribute("class", "character-marker");
      g.setAttribute("pointer-events", "none");
      var ring = document.createElementNS(NS, "circle");
      ring.setAttribute("class", "character-marker-ring");
      ring.setAttribute("r", "34");
      var token = document.createElementNS(NS, "circle");
      token.setAttribute("class", "character-marker-token");
      token.setAttribute("r", "9");
      token.setAttribute("cy", "-34");
      g.appendChild(ring);
      g.appendChild(token);
      svg.appendChild(g);
    }
    setMarkerPos(g, x, y);
    mapState.markerPos = { x: x, y: y };
    return g;
  }

  function setMarkerPos(g, x, y) {
    g.setAttribute("transform", "translate(" + x + "," + y + ")");
  }

  function clearCopies() {
    mapState.copies.forEach(function (el) {
      if (el && el.parentNode) el.parentNode.removeChild(el);
    });
    mapState.copies = [];
  }

  function cancelAnim() {
    if (mapState.animFrame) {
      window.cancelAnimationFrame(mapState.animFrame);
      mapState.animFrame = null;
    }
  }

  function snapToFinal() {
    cancelAnim();
    var finalState = mapState.pendingFinal;
    clearCopies();
    if (finalState && finalState.x != null) {
      ensureMarker(finalState.x, finalState.y);
    }
    mapState.pendingFinal = null;
  }

  function easeOut(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function animateAlong(from, to, el, duration, onDone) {
    var start = null;
    function tick(ts) {
      if (start == null) start = ts;
      var t = Math.min(1, (ts - start) / duration);
      var e = easeOut(t);
      var x = from.x + (to.x - from.x) * e;
      var y = from.y + (to.y - from.y) * e;
      setMarkerPos(el, x, y);
      if (t < 1) {
        mapState.animFrame = window.requestAnimationFrame(tick);
      } else if (onDone) {
        mapState.animFrame = null;
        onDone();
      }
    }
    mapState.animFrame = window.requestAnimationFrame(tick);
  }

  function travelKey(fromId, completedAt) {
    return "adventure-travel:" + mapState.adventureId + ":" + fromId + ":" + (completedAt || "na");
  }

  function markSeen(key) {
    try {
      if (key) sessionStorage.setItem(key, "1");
    } catch (err) { /* private mode */ }
  }

  function wasSeen(key) {
    try {
      return key ? !!sessionStorage.getItem(key) : false;
    } catch (err) {
      return false;
    }
  }

  function successorsOf(fromId) {
    var edges = (mapState.state && mapState.state.edges) || [];
    var prog = progressByNode();
    var dests = [];
    edges.forEach(function (edge) {
      if (edge.from_node_id !== fromId) return;
      var node = nodeById(edge.to_node_id);
      var p = prog[edge.to_node_id];
      if (node && p && p.status === "available") dests.push(node);
    });
    return dests;
  }

  function announceUnlocks(nodes) {
    if (!nodes || !nodes.length) return;
    var titles = nodes.map(function (n) { return n.title; }).join(", ");
    announce("Unlocked: " + titles);
  }

  function playTravel(fromNode, destNodes, seenKey) {
    destNodes = destNodes || [];
    markSeen(seenKey);
    var from = { x: fromNode.x, y: fromNode.y };
    var marker = ensureMarker(from.x, from.y);

    if (!destNodes.length) {
      mapState.pendingFinal = from;
      return;
    }

    announceUnlocks(destNodes);

    if (prefersReducedMotion()) {
      if (destNodes.length === 1) {
        ensureMarker(destNodes[0].x, destNodes[0].y);
        mapState.pendingFinal = { x: destNodes[0].x, y: destNodes[0].y };
      } else {
        ensureMarker(from.x, from.y);
        mapState.pendingFinal = from;
      }
      return;
    }

    if (destNodes.length === 1) {
      var dest = destNodes[0];
      mapState.pendingFinal = { x: dest.x, y: dest.y };
      animateAlong(from, dest, marker, TRAVEL_MS, function () {
        ensureMarker(dest.x, dest.y);
        mapState.pendingFinal = null;
      });
      return;
    }

    mapState.pendingFinal = from;
    destNodes.forEach(function (dest) {
      var copy = marker.cloneNode(true);
      copy.removeAttribute("id");
      copy.setAttribute("class", "character-marker character-marker-copy");
      mapState.svg.appendChild(copy);
      mapState.copies.push(copy);
      var start = { x: from.x, y: from.y };
      var end = { x: dest.x, y: dest.y };
      var begun = null;
      function tick(ts) {
        if (begun == null) begun = ts;
        var t = Math.min(1, (ts - begun) / TRAVEL_MS);
        var e = easeOut(t);
        setMarkerPos(copy, start.x + (end.x - start.x) * e, start.y + (end.y - start.y) * e);
        copy.style.opacity = String(1 - t);
        if (t < 1) window.requestAnimationFrame(tick);
        else if (copy.parentNode) copy.parentNode.removeChild(copy);
      }
      window.requestAnimationFrame(tick);
    });
  }

  function inferPendingTravel() {
    var rows = (mapState.state && mapState.state.my_progress && mapState.state.my_progress.nodes) || [];
    var latest = null;
    rows.forEach(function (p) {
      if (p.status !== "completed" || !p.completed_at) return;
      if (!latest || p.completed_at > latest.completed_at) latest = p;
    });
    if (!latest) return null;
    var fromNode = nodeById(latest.node_id);
    if (!fromNode) return null;
    var key = travelKey(latest.node_id, latest.completed_at);
    if (wasSeen(key)) return null;
    var dests = successorsOf(latest.node_id);
    return { fromNode: fromNode, dests: dests, key: key };
  }

  function overviewFits() {
    var box = mapState.container;
    var svg = mapState.svg;
    if (!box || !svg) return true;
    var width = parseInt(svg.getAttribute("width"), 10) || 0;
    var height = parseInt(svg.getAttribute("height"), 10) || 0;
    return width <= box.clientWidth + 8 && height <= box.clientHeight + 8;
  }

  function jumpTo(x, y) {
    interrupt();
    var box = mapState.container;
    if (!box) return;
    box.scrollTo({
      left: Math.max(0, x - box.clientWidth / 2),
      top: Math.max(0, y - box.clientHeight / 2),
      behavior: prefersReducedMotion() ? "auto" : "smooth",
    });
  }

  function drawOverview() {
    var nav = mapState.overview;
    var mini = mapState.overviewSvg;
    var state = mapState.state;
    if (!nav || !mini || !state) return;

    if (overviewFits()) {
      nav.hidden = true;
      nav.setAttribute("aria-hidden", "true");
      return;
    }
    nav.hidden = false;
    nav.removeAttribute("aria-hidden");

    while (mini.firstChild) mini.removeChild(mini.firstChild);
    var advW = (state.adventure && state.adventure.width) || 2000;
    var advH = (state.adventure && state.adventure.height) || 1500;
    var viewW = 180;
    var viewH = Math.max(90, Math.round(viewW * (advH / advW)));
    mini.setAttribute("viewBox", "0 0 " + advW + " " + advH);
    mini.setAttribute("width", String(viewW));
    mini.setAttribute("height", String(viewH));

    (state.edges || []).forEach(function (edge) {
      var from = nodeById(edge.from_node_id);
      var to = nodeById(edge.to_node_id);
      if (!from || !to) return;
      var line = document.createElementNS(NS, "line");
      line.setAttribute("x1", from.x);
      line.setAttribute("y1", from.y);
      line.setAttribute("x2", to.x);
      line.setAttribute("y2", to.y);
      line.setAttribute("class", "overview-edge");
      mini.appendChild(line);
    });

    var prog = progressByNode();
    (state.nodes || []).forEach(function (node) {
      var p = prog[node.id] || { status: "locked" };
      var unlocked = p.status === "available" || p.status === "in_progress" || p.status === "completed";
      var mark = document.createElementNS(NS, "circle");
      mark.setAttribute("cx", node.x);
      mark.setAttribute("cy", node.y);
      mark.setAttribute("r", 28);
      mark.setAttribute("class", "overview-node overview-status-" + p.status);
      mark.setAttribute("data-node-id", node.id);
      if (unlocked) {
        mark.setAttribute("tabindex", "0");
        mark.setAttribute("role", "button");
        mark.setAttribute("aria-label", "Jump to " + node.title);
        mark.addEventListener("click", function (evt) {
          evt.stopPropagation();
          jumpTo(node.x, node.y);
        });
        mark.addEventListener("keydown", function (evt) {
          if (evt.key === "Enter" || evt.key === " ") {
            evt.preventDefault();
            jumpTo(node.x, node.y);
          }
        });
      }
      mini.appendChild(mark);
    });

    if (mapState.markerPos) {
      var dot = document.createElementNS(NS, "circle");
      dot.setAttribute("cx", mapState.markerPos.x);
      dot.setAttribute("cy", mapState.markerPos.y);
      dot.setAttribute("r", 18);
      dot.setAttribute("class", "overview-marker");
      mini.appendChild(dot);
    }

    var box = mapState.container;
    var rect = document.createElementNS(NS, "rect");
    rect.setAttribute("class", "overview-viewport");
    rect.setAttribute("x", String(box.scrollLeft));
    rect.setAttribute("y", String(box.scrollTop));
    rect.setAttribute("width", String(box.clientWidth));
    rect.setAttribute("height", String(box.clientHeight));
    mini.appendChild(rect);
  }

  function onOverviewPointer(evt) {
    if (evt.target && evt.target.closest && evt.target.closest(".overview-node")) return;
    var mini = mapState.overviewSvg;
    if (!mini) return;
    var pt = mini.createSVGPoint();
    pt.x = evt.clientX;
    pt.y = evt.clientY;
    var ctm = mini.getScreenCTM();
    if (!ctm) return;
    var loc = pt.matrixTransform(ctm.inverse());
    jumpTo(loc.x, loc.y);
  }

  function bindOverview() {
    if (!mapState.overviewSvg || !mapState.container) return;
    mapState.overviewSvg.addEventListener("click", onOverviewPointer);
    mapState.container.addEventListener("scroll", function () {
      drawOverview();
    }, { passive: true });
    window.addEventListener("resize", function () {
      drawOverview();
    });
  }

  function interrupt() {
    snapToFinal();
  }

  function refresh(state, travelOpts) {
    mapState.state = state;
    cancelAnim();
    clearCopies();

    var origin = markerOrigin();
    if (origin) ensureMarker(origin.x, origin.y);

    if (travelOpts && travelOpts.fromNodeId != null) {
      var fromNode = nodeById(travelOpts.fromNodeId) || origin;
      var dests = (travelOpts.nextUnlocked || []).map(function (item) {
        return nodeById(item.id) || item;
      }).filter(Boolean);
      var completedAt = travelOpts.completedAt;
      if (!completedAt) {
        var prog = progressByNode()[travelOpts.fromNodeId];
        completedAt = prog && prog.completed_at;
      }
      if (fromNode) playTravel(fromNode, dests, travelKey(travelOpts.fromNodeId, completedAt));
    } else {
      var pending = inferPendingTravel();
      if (pending) playTravel(pending.fromNode, pending.dests, pending.key);
    }

    drawOverview();
  }

  window.AdventurePlayerMap = {
    init: function (opts) {
      mapState.adventureId = opts && opts.adventureId;
      mapState.svg = document.getElementById("adventure-map");
      mapState.container = document.getElementById("map-container");
      mapState.live = document.getElementById("player-live-region");
      mapState.overview = document.getElementById("adventure-overview");
      mapState.overviewSvg = document.getElementById("adventure-overview-svg");
      bindOverview();
    },
    refresh: refresh,
    interrupt: interrupt,
    announce: announce,
    jumpTo: jumpTo,
  };
})();
