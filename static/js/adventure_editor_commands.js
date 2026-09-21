/**
 * Editor keyboard, canvas zoom, and session-only undo/redo.
 */
(function () {
  "use strict";

  var MIN_ZOOM = 0.6;
  var MAX_ZOOM = 1.6;
  var ZOOM_STEP = 0.1;

  var cmds = {
    canEdit: false,
    zoom: 1,
    stack: [],
    index: -1,
    selectedNodeId: null,
    selectedEdgeId: null,
    api: null,
    adventureId: null,
  };

  function announce(message, kind) {
    var el = document.getElementById("editor-validation");
    if (!el || !message) return;
    el.className = "alert " + (kind === "error" ? "alert-danger" : kind === "success" ? "alert-success" : "alert-info");
    el.textContent = message;
    el.classList.remove("d-none");
  }

  function applyZoom() {
    var inner = document.getElementById("editor-zoom-inner");
    if (!inner) return;
    inner.style.transform = "scale(" + cmds.zoom + ")";
    inner.style.transformOrigin = "0 0";
  }

  function setZoom(next) {
    cmds.zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.round(next * 10) / 10));
    applyZoom();
    announce("Zoom " + Math.round(cmds.zoom * 100) + "%", "info");
  }

  function nodes() {
    return (window.AdventureEditor && AdventureEditor.getState && AdventureEditor.getState().nodes) || [];
  }

  function edges() {
    return (window.AdventureEditor && AdventureEditor.getState && AdventureEditor.getState().edges) || [];
  }

  function nodeById(id) {
    return nodes().find(function (n) { return n.id === id; }) || null;
  }

  function edgeById(id) {
    return edges().find(function (e) { return e.id === id; }) || null;
  }

  function focusNodeGroup(nodeId) {
    var svg = document.getElementById("adventure-canvas");
    if (!svg) return;
    var g = svg.querySelector('.map-node[data-node-id="' + nodeId + '"]');
    if (g && g.focus) g.focus();
  }

  function nearestNode(from, dirX, dirY) {
    var best = null;
    var bestScore = Infinity;
    nodes().forEach(function (n) {
      if (!from || n.id === from.id) return;
      var dx = n.x - from.x;
      var dy = n.y - from.y;
      if (dirX && dx * dirX <= 4) return;
      if (dirY && dy * dirY <= 4) return;
      var dist = Math.hypot(dx, dy);
      var align = dirX ? Math.abs(dy) : Math.abs(dx);
      var score = dist + align * 0.5;
      if (score < bestScore) {
        bestScore = score;
        best = n;
      }
    });
    return best;
  }

  function isTypingTarget(el) {
    if (!el || !el.tagName) return false;
    var tag = el.tagName.toLowerCase();
    if (tag === "input" || tag === "textarea" || tag === "select") return true;
    return !!el.isContentEditable;
  }

  function runCommand(entry, direction) {
    var fn = direction === "undo" ? entry.undo : entry.redo;
    if (!fn) return Promise.resolve(false);
    return Promise.resolve(fn()).then(function (body) {
      if (body && body.success === false) {
        announce("Could not " + direction + " that change.", "error");
        return false;
      }
      if (window.AdventureEditor && AdventureEditor.refreshGraph) {
        AdventureEditor.refreshGraph();
      }
      return true;
    }).catch(function () {
      announce("Could not " + direction + " that change.", "error");
      return false;
    });
  }

  function undo() {
    if (!cmds.canEdit) return;
    if (cmds.index < 0) {
      announce("Nothing to undo.", "info");
      return;
    }
    var entry = cmds.stack[cmds.index];
    runCommand(entry, "undo").then(function (ok) {
      if (ok) {
        cmds.index -= 1;
        announce("Undid " + (entry.label || "edit") + ".", "success");
      }
    });
  }

  function redo() {
    if (!cmds.canEdit) return;
    if (cmds.index >= cmds.stack.length - 1) {
      announce("Nothing to redo.", "info");
      return;
    }
    var entry = cmds.stack[cmds.index + 1];
    runCommand(entry, "redo").then(function (ok) {
      if (ok) {
        cmds.index += 1;
        announce("Redid " + (entry.label || "edit") + ".", "success");
      }
    });
  }

  function record(entry) {
    if (!cmds.canEdit || !entry) return;
    cmds.stack = cmds.stack.slice(0, cmds.index + 1);
    cmds.stack.push(entry);
    cmds.index = cmds.stack.length - 1;
  }

  function confirmDelete() {
    if (!cmds.canEdit) return;
    var node = nodeById(cmds.selectedNodeId);
    if (node) {
      if (!window.confirm("Delete node \"" + node.slug + "\" and its connections?")) return;
      if (window.AdventureEditor && AdventureEditor.deleteSelectedNode) {
        AdventureEditor.deleteSelectedNode(node);
      }
      return;
    }
    var edge = edgeById(cmds.selectedEdgeId);
    if (edge) {
      if (!window.confirm("Delete this connection?")) return;
      if (window.AdventureEditor && AdventureEditor.deleteSelectedEdge) {
        AdventureEditor.deleteSelectedEdge(edge);
      }
    }
  }

  function onKeydown(evt) {
    if (document.querySelector(".modal.show")) return;
    var key = evt.key;
    var meta = evt.ctrlKey || evt.metaKey;

    if (meta && (key === "z" || key === "Z")) {
      if (isTypingTarget(evt.target)) return;
      evt.preventDefault();
      if (evt.shiftKey) redo();
      else undo();
      return;
    }
    if (meta && (key === "y" || key === "Y")) {
      if (isTypingTarget(evt.target)) return;
      evt.preventDefault();
      redo();
      return;
    }

    if (isTypingTarget(evt.target)) return;

    if (key === "=" || key === "+") {
      evt.preventDefault();
      setZoom(cmds.zoom + ZOOM_STEP);
      return;
    }
    if (key === "-" || key === "_") {
      evt.preventDefault();
      setZoom(cmds.zoom - ZOOM_STEP);
      return;
    }

    if (key === "Escape") {
      cmds.selectedNodeId = null;
      cmds.selectedEdgeId = null;
      if (window.AdventureEditor && AdventureEditor.clearInspector) {
        AdventureEditor.clearInspector();
      }
      var canvas = document.getElementById("adventure-canvas");
      if (canvas) canvas.focus();
      announce("Selection cleared.", "info");
      return;
    }

    if (!cmds.canEdit) return;

    if (key === "Enter") {
      var focused = document.activeElement;
      var id = focused && focused.getAttribute && focused.getAttribute("data-node-id");
      if (id) {
        evt.preventDefault();
        var node = nodeById(parseInt(id, 10));
        if (node && window.AdventureEditor && AdventureEditor.inspectNode) {
          AdventureEditor.inspectNode(node);
        }
      }
      return;
    }

    if (key === "Delete" || key === "Backspace") {
      evt.preventDefault();
      confirmDelete();
      return;
    }

    if (key === "ArrowLeft" || key === "ArrowRight" || key === "ArrowUp" || key === "ArrowDown") {
      evt.preventDefault();
      var current = nodeById(cmds.selectedNodeId) || (function () {
        var fid = document.activeElement && document.activeElement.getAttribute && document.activeElement.getAttribute("data-node-id");
        return fid ? nodeById(parseInt(fid, 10)) : nodes()[0];
      })();
      var next = nearestNode(
        current,
        key === "ArrowLeft" ? -1 : key === "ArrowRight" ? 1 : 0,
        key === "ArrowUp" ? -1 : key === "ArrowDown" ? 1 : 0
      );
      if (next) {
        cmds.selectedNodeId = next.id;
        focusNodeGroup(next.id);
        announce("Focused " + next.title + ", " + next.node_type + ".", "info");
      }
    }
  }

  window.AdventureEditorCommands = {
    init: function (opts) {
      cmds.canEdit = !!(opts && opts.canEdit);
      cmds.api = opts && opts.api;
      cmds.adventureId = opts && opts.adventureId;
      cmds.stack = [];
      cmds.index = -1;
      cmds.zoom = 1;
      applyZoom();
      document.addEventListener("keydown", onKeydown);
    },
    record: record,
    undo: undo,
    redo: redo,
    setSelection: function (nodeId, edgeId) {
      cmds.selectedNodeId = nodeId || null;
      cmds.selectedEdgeId = edgeId || null;
      var node = nodeById(cmds.selectedNodeId);
      if (node) announce("Selected " + node.title + ", " + node.node_type + ".", "info");
    },
    getZoom: function () { return cmds.zoom; },
    announce: announce,
  };
})();
