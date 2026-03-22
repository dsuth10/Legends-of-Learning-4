/**
 * Registry for modular classroom display tools.
 * Each tool: class with constructor(config, containerEl), start(), stop(), destroy().
 */
(function (global) {
  'use strict';

  const tools = {};

  const ToolRegistry = {
    register(name, ToolClass) {
      if (!name || typeof ToolClass !== 'function') {
        throw new Error('ToolRegistry.register: invalid tool');
      }
      tools[name] = ToolClass;
    },

    create(name, config, container) {
      const ToolClass = tools[name];
      if (!ToolClass) {
        throw new Error('Unknown tool: ' + name);
      }
      return new ToolClass(config, container);
    },

    has(name) {
      return Object.prototype.hasOwnProperty.call(tools, name);
    },
  };

  global.ToolRegistry = ToolRegistry;
})(typeof window !== 'undefined' ? window : globalThis);
