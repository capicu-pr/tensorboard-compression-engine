from __future__ import annotations

"""
TensorBoard Compression plugin.
"""

import json
from typing import Any, Dict

from tensorboard.backend import http_util
from tensorboard.plugins import base_plugin
from tensorboard.plugins.scalar import plugin_data_pb2
from tensorboard import plugin_util
from werkzeug.wrappers import Request, Response


class CompressionPlugin(base_plugin.TBPlugin):
    """TensorBoard plugin that provides a Compression dashboard tab."""

    plugin_name = "compression"

    def __init__(self, context: base_plugin.TBContext) -> None:
        super().__init__(context)
        self._context = context

    def is_active(self) -> bool:
        """Return True if the plugin should be shown."""
        try:
            multiplexer = getattr(self._context, "multiplexer", None)
            if not multiplexer:
                return True
            runs = multiplexer.Runs()
            if not runs:
                return True
            # Check if any run has compression tags by testing a known tag
            for run_name in runs.keys():
                try:
                    # Test if compression/speedup tag exists
                    events = multiplexer.Scalars(run_name, f"{run_name}/compression/speedup")
                    if events:
                        return True
                except Exception:
                    continue
            return True
        except Exception:
            return True

    def frontend_metadata(self):
        """Return frontend metadata."""
        # Use es_module_path pointing to an ES module that renders our HTML
        # TensorBoard does: "." + module_path, so:
        # - "/render.js" → ".render.js" (wrong - missing /)
        # - "render.js" → ".render.js" (wrong - missing /)
        # - "/render.js" with base href "plugin/compression/" should work
        # Actually, TensorBoard prepends "." so "/render.js" becomes ".render.js"
        # We need it to be "./render.js", so we use "/render.js" which becomes ".render.js"
        # But wait, that's still wrong. Let me check the base href resolution...
        # Base href is "plugin/compression/", so ".render.js" resolves to "plugin/compression/.render.js"
        # We need "./render.js" which resolves to "plugin/compression/render.js"
        # So we need module_path to be "/render.js" so TensorBoard makes it ".render.js"
        # But that's still wrong! The issue is TensorBoard prepends "." not "./"
        # Solution: Use "/render.js" so TensorBoard creates ".render.js", but we need "./render.js"
        # Actually, I think the path should start with "/" to get "./render.js" after TensorBoard's processing
        return base_plugin.FrontendMetadata(
            # TensorBoard does: "." + es_module_path for import
            # Iframe loads from /data/plugin_entry.html?name=compression
            # Base href is "plugin/compression/" but ES modules don't respect <base>
            # So import("./render.js") resolves to /data/render.js (wrong!)
            # We need import("./plugin/compression/render.js") to resolve to /data/plugin/compression/render.js
            # So es_module_path should be "/plugin/compression/render.js"
            # But TensorBoard also constructs module_path as: /data/plugin/{name}{es_module_path}
            # That would give: /data/plugin/compression/plugin/compression/render.js (duplicate!)
            # Wait - let me check: module_path is only used for the metadata, not the actual import
            # The import uses es_module_path directly: "." + es_module_path
            # So if es_module_path="/plugin/compression/render.js", import becomes "./plugin/compression/render.js"
            # Which resolves from /data/plugin_entry.html to /data/plugin/compression/render.js ✓
            es_module_path="/plugin/compression/render.js",
            tab_name="COMPRESSION",
            disable_reload=False,
        )

    def get_plugin_apps(self) -> Dict[str, Any]:
        # Return handlers directly - TensorBoard will call them with (environ, start_response).
        # Routes must start with a slash.
        return {
            "/": self._serve_index,
            "/render.js": self._serve_render_module,
            "/api/summary": self._serve_summary,
        }
    
    def _serve_render_module(self, environ, start_response):
        """Serve an ES module that renders our HTML directly."""
        request = Request(environ)
        # ES module that renders HTML and fetches data (all in one, no inline scripts)
        js = """
export function render() {
  // Set up the HTML structure
  document.body.innerHTML = `
    <style>
      body { font-family: sans-serif; margin: 16px; background: #202124; color: #e8eaed; }
      h1 { font-size: 20px; margin-bottom: 4px; }
      table { border-collapse: collapse; margin-top: 12px; width: 100%; font-size: 13px; }
      th, td { border-bottom: 1px solid #3c4043; padding: 6px 8px; text-align: right; }
      th { text-align: left; background: #303134; font-weight: 600; }
      tr:nth-child(even) { background: #292a2d; }
      tr:hover { background: #3c4043; }
      .run-name { text-align: left; font-weight: 600; }
    </style>
    <h1>Compression Dashboard</h1>
    <div id="root">Loading...</div>
  `;
  
  // Fetch data and render table
  const apiUrl = '/data/plugin/compression/api/summary';
  console.log('Fetching from:', apiUrl);
  fetch(apiUrl)
    .then(r => {
      console.log('Response status:', r.status);
      if (!r.ok) {
        throw new Error('HTTP ' + r.status + ': ' + r.statusText);
      }
      return r.json();
    })
    .then(data => {
      console.log('Received data:', data);
      const root = document.getElementById('root');
      if (!data.runs || data.runs.length === 0) {
        root.textContent = 'No compression data found.';
        return;
      }
      const formatVal = (val) => val !== null && val !== undefined ? val.toFixed(4) : '-';
      const formatRatio = (val) => val !== null && val !== undefined ? val.toFixed(2) + 'x' : '-';
      let html = '<table><thead><tr><th class="run-name">Run</th><th>FP32 Acc</th><th>INT8 Acc</th><th>Accuracy Drop</th><th>Size Ratio</th><th>Speedup</th><th>Memory Reduction (MB)</th><th>Energy Reduction (mW)</th></tr></thead><tbody>';
      data.runs.forEach(r => {
        html += '<tr>' +
          '<td class="run-name">' + r.run + '</td>' +
          '<td>' + formatVal(r.accuracy_fp32) + '</td>' +
          '<td>' + formatVal(r.accuracy_int8) + '</td>' +
          '<td>' + formatVal(r.accuracy_drop) + '</td>' +
          '<td>' + formatRatio(r.size_ratio) + '</td>' +
          '<td>' + formatRatio(r.speedup) + '</td>' +
          '<td>' + formatVal(r.memory_reduction_mb) + '</td>' +
          '<td>' + formatVal(r.energy_reduction_mw) + '</td>' +
          '</tr>';
      });
      html += '</tbody></table>';
      root.innerHTML = html;
    })
    .catch(e => {
      console.error('Error:', e);
      const root = document.getElementById('root');
      if (root) {
        root.textContent = 'Error: ' + e.message;
      }
    });
}
"""
        response = http_util.Respond(request, js, content_type="application/javascript")
        return response(environ, start_response)
    

    def _serve_index(self, environ, start_response):
        """Serve the dashboard HTML."""
        request = Request(environ)
        html = """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Compression Dashboard</title>
  <style>
    body { font-family: sans-serif; margin: 16px; background: #202124; color: #e8eaed; }
    h1 { font-size: 20px; margin-bottom: 4px; }
    table { border-collapse: collapse; margin-top: 12px; width: 100%; font-size: 13px; }
    th, td { border-bottom: 1px solid #3c4043; padding: 6px 8px; text-align: right; }
    th { text-align: left; background: #303134; font-weight: 600; }
    tr:nth-child(even) { background: #292a2d; }
    tr:hover { background: #3c4043; }
    .run-name { text-align: left; font-weight: 600; }
  </style>
</head>
<body>
  <h1>Compression Dashboard</h1>
  <div id="root">Loading...</div>
  <script>
    // Use absolute path for API call - TensorBoard serves plugins at /data/plugin/{plugin_name}/
    const apiUrl = '/data/plugin/compression/api/summary';
    console.log('Fetching from:', apiUrl);
    fetch(apiUrl)
      .then(r => {
        console.log('Response status:', r.status);
        if (!r.ok) {
          throw new Error('HTTP ' + r.status + ': ' + r.statusText);
        }
        return r.json();
      })
      .then(data => {
        console.log('Received data:', data);
        const root = document.getElementById('root');
        if (!data.runs || data.runs.length === 0) {
          root.textContent = 'No compression data found.';
          return;
        }
        let html = '<table><thead><tr><th class="run-name">Run</th><th>FP32 Acc</th><th>INT8 Acc</th><th>Accuracy Drop</th><th>Size Ratio</th><th>Speedup</th><th>Memory Reduction (MB)</th><th>Energy Reduction (mW)</th></tr></thead><tbody>';
        data.runs.forEach(r => {
          const formatVal = (val) => val !== null && val !== undefined ? val.toFixed(4) : '-';
          const formatRatio = (val) => val !== null && val !== undefined ? val.toFixed(2) + 'x' : '-';
          html += `<tr>
            <td class="run-name">${r.run}</td>
            <td>${formatVal(r.accuracy_fp32)}</td>
            <td>${formatVal(r.accuracy_int8)}</td>
            <td>${formatVal(r.accuracy_drop)}</td>
            <td>${formatRatio(r.size_ratio)}</td>
            <td>${formatRatio(r.speedup)}</td>
            <td>${formatVal(r.memory_reduction_mb)}</td>
            <td>${formatVal(r.energy_reduction_mw)}</td>
          </tr>`;
        });
        html += '</tbody></table>';
        root.innerHTML = html;
      })
      .catch(e => {
        console.error('Error:', e);
        document.getElementById('root').textContent = 'Error: ' + e.message;
      });
  </script>
</body>
</html>"""
        # Return Response object as WSGI app - call it to get iterable
        response = http_util.Respond(request, html, content_type="text/html")
        return response(environ, start_response)

    def _serve_summary(self, environ, start_response):
        """Return compression metrics as JSON."""
        request = Request(environ)
        try:
            # Try data_provider first (new API), fall back to multiplexer (old API)
            data_provider = getattr(self._context, "data_provider", None)
            multiplexer = getattr(self._context, "multiplexer", None)
            
            if data_provider:
                # Use data_provider API (like scalars plugin does)
                from tensorboard.data import provider
                from tensorboard.plugins.scalar import metadata as scalar_metadata
                
                ctx = plugin_util.context(environ)
                experiment = plugin_util.experiment_id(environ)
                
                # List all scalar tags
                scalar_mapping = data_provider.list_scalars(
                    ctx,
                    experiment_id=experiment,
                    plugin_name=scalar_metadata.PLUGIN_NAME,
                )
                
                runs_data = []
                for run_name, tag_to_metadata in scalar_mapping.items():
                    # Check if this run has compression tags
                    compression_tags = [t for t in tag_to_metadata.keys() if "compression/" in t]
                    if not compression_tags:
                        continue
                    
                    # Read scalar values for this run
                    run_tag_filter = provider.RunTagFilter(runs=[run_name])
                    all_scalars = data_provider.read_scalars(
                        ctx,
                        experiment_id=experiment,
                        plugin_name=scalar_metadata.PLUGIN_NAME,
                        downsample=500,
                        run_tag_filter=run_tag_filter,
                    )
                    
                    run_scalars = all_scalars.get(run_name, {})
                    
                    def get_scalar(tag_suffix):
                        full_tag = f"{run_name}/{tag_suffix}"
                        scalars = run_scalars.get(full_tag)
                        if scalars:
                            return float(scalars[-1].value)
                        return None
                    
                    runs_data.append({
                        "run": run_name,
                        "accuracy_fp32": get_scalar("metrics/accuracy/fp32"),
                        "accuracy_int8": get_scalar("metrics/accuracy/int8"),
                        "accuracy_drop": get_scalar("compression/accuracy_drop"),
                        "size_ratio": get_scalar("compression/size_ratio"),
                        "speedup": get_scalar("compression/speedup"),
                        "memory_reduction_mb": get_scalar("compression/memory_reduction_mb"),
                        "energy_reduction_mw": get_scalar("compression/energy_reduction_mw"),
                    })
                
                body = json.dumps({"runs": runs_data})
            elif multiplexer:
                # Fall back to old multiplexer API - use accumulator directly
                runs_data = []
                runs = multiplexer.Runs()
                
                for run_name in runs.keys():
                    try:
                        accumulator = multiplexer.GetAccumulator(run_name)
                        if not accumulator:
                            continue
                        
                        tags_dict = accumulator.Tags()
                        tags = tags_dict.get("scalars", [])
                        if not tags:
                            continue
                        
                        compression_tags = [t for t in tags if "compression/" in t]
                        if not compression_tags:
                            continue
                        
                        # Get scalar values from accumulator.scalars
                        def get_scalar(tag_suffix):
                            full_tag = f"{run_name}/{tag_suffix}"
                            try:
                                items = accumulator.scalars.Items(full_tag)
                                return float(items[-1].value) if items else None
                            except Exception:
                                return None
                        
                        runs_data.append({
                            "run": run_name,
                            "accuracy_fp32": get_scalar("metrics/accuracy/fp32"),
                            "accuracy_int8": get_scalar("metrics/accuracy/int8"),
                            "accuracy_drop": get_scalar("compression/accuracy_drop"),
                            "size_ratio": get_scalar("compression/size_ratio"),
                            "speedup": get_scalar("compression/speedup"),
                            "memory_reduction_mb": get_scalar("compression/memory_reduction_mb"),
                            "energy_reduction_mw": get_scalar("compression/energy_reduction_mw"),
                        })
                    except Exception:
                        continue
                
                body = json.dumps({"runs": runs_data})
            else:
                body = json.dumps({"runs": [], "error": "neither data_provider nor multiplexer available"})
        except Exception as e:
            body = json.dumps({"runs": [], "error": str(e)})
        
        # Return Response object as WSGI app - call it to get iterable
        response = http_util.Respond(request, body, content_type="application/json")
        return response(environ, start_response)
