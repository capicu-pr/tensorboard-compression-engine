from __future__ import annotations

"""
TensorBoard Compression plugin.
"""

import json
from typing import Any, Dict

from tensorboard.backend import http_util
from tensorboard.plugins import base_plugin
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
        return base_plugin.FrontendMetadata(
            # TensorBoard does: "." + es_module_path for import
            # Iframe loads from /data/plugin_entry.html?name=compression
            # Base href is "plugin/compression/" but ES modules don't respect <base>
            # So import("./render.js") resolves to /data/render.js (wrong!)
            # We need import("./plugin/compression/render.js") to resolve to /data/plugin/compression/render.js
            # So es_module_path should be "/plugin/compression/render.js"
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
  // Get theme colors from TensorBoard's parent window
  // TensorBoard uses CSS variables and computed styles that change with theme toggle
  function getThemeColors() {
    let colors = {
      bgColor: '#202124',
      textColor: '#e8eaed',
      fontFamily: 'Roboto, sans-serif',
      fontSize: '13px',
      borderColor: '#3c4043',
      hoverBg: '#3c4043',
      headerBg: '#303134',
      evenRowBg: '#292a2d',
      cardBg: '#303134',
      cardHeaderBg: '#2d2e31',
      sidebarBg: '#202124',
      secondaryText: '#9aa0a6'
    };
    
    try {
      if (window.parent && window.parent !== window) {
        const parentDoc = window.parent.document;
        const parentBody = parentDoc.body;
        
        if (parentBody) {
          const computed = window.parent.getComputedStyle(parentBody);
          
          // Get background and text colors from parent body
          const parentBg = computed.backgroundColor;
          const parentText = computed.color;
          const parentFont = computed.fontFamily;
          const parentFontSize = computed.fontSize;
          
          // Try to find TensorBoard's main content area or sidebar for accurate colors
          // Look for common TensorBoard container classes
          let contentElement = parentDoc.querySelector('.tb-main-content') || 
                               parentDoc.querySelector('.main-content') ||
                               parentDoc.querySelector('[class*="content"]') ||
                               parentBody;
          
          let sidebarElement = parentDoc.querySelector('.tb-sidebar') ||
                              parentDoc.querySelector('.sidebar') ||
                              parentDoc.querySelector('[class*="sidebar"]') ||
                              parentBody;
          
          const contentComputed = window.parent.getComputedStyle(contentElement);
          const sidebarComputed = window.parent.getComputedStyle(sidebarElement);
          
          // Use computed styles from TensorBoard's actual elements
          colors.bgColor = sidebarComputed.backgroundColor || parentBg || colors.bgColor;
          colors.sidebarBg = sidebarComputed.backgroundColor || parentBg || colors.sidebarBg;
          colors.headerBg = contentComputed.backgroundColor || parentBg || colors.headerBg;
          colors.textColor = contentComputed.color || parentText || colors.textColor;
          colors.fontFamily = contentComputed.fontFamily || parentFont || colors.fontFamily;
          colors.fontSize = contentComputed.fontSize || parentFontSize || colors.fontSize;
          
          // Try to get border color from computed styles - check multiple sources
          const borderSampleElements = [
            parentDoc.querySelector('.card'),
            parentDoc.querySelector('[class*="card"]'),
            parentDoc.querySelector('table'),
            parentDoc.querySelector('td'),
            parentDoc.querySelector('th'),
            parentDoc.querySelector('[class*="border"]'),
            contentElement
          ].filter(el => el !== null);
          
          for (const borderEl of borderSampleElements) {
            try {
              const borderComputed = window.parent.getComputedStyle(borderEl);
              const borderColor = borderComputed.borderColor || 
                                 borderComputed.borderTopColor ||
                                 borderComputed.borderBottomColor;
              if (borderColor && 
                  borderColor !== 'rgba(0, 0, 0, 0)' && 
                  borderColor !== 'transparent' &&
                  borderColor !== colors.bgColor) {
                colors.borderColor = borderColor;
                break;
              }
            } catch (e) {
              // Skip this element
            }
          }
          
          // Try to get hover background color from actual hoverable elements
          const hoverableElements = [
            parentDoc.querySelector('button'),
            parentDoc.querySelector('[class*="button"]'),
            parentDoc.querySelector('[class*="btn"]'),
            parentDoc.querySelector('tr'),
            parentDoc.querySelector('[class*="hover"]'),
            parentDoc.querySelector('[class*="clickable"]')
          ].filter(el => el !== null);
          
          for (const hoverEl of hoverableElements) {
            try {
              // We can't directly get :hover styles, but we can check if element has hover styles
              // by looking at its computed styles and inferring from similar elements
              const hoverComputed = window.parent.getComputedStyle(hoverEl);
              // For now, we'll calculate it, but try to find similar colored elements
            } catch (e) {
              // Skip
            }
          }
          
          // Determine theme based on background color lightness
          const bgRgb = parseRgb(colors.bgColor);
          if (bgRgb) {
            const lightness = (bgRgb.r + bgRgb.g + bgRgb.b) / 3;
            const isDarkTheme = lightness < 128;
            
            if (isDarkTheme) {
              // Dark theme - use dark colors
              colors.hoverBg = adjustBrightness(colors.bgColor, 20);
              colors.evenRowBg = adjustBrightness(colors.bgColor, -10);
              colors.cardBg = '#303134';
              colors.cardHeaderBg = '#2d2e31';
            } else {
              // Light theme - use light colors
              colors.hoverBg = adjustBrightness(colors.bgColor, -10);
              colors.evenRowBg = '#ffffff';
              colors.borderColor = '#e0e0e0';
              colors.secondaryText = '#5f6368';
              colors.cardBg = '#ffffff';
              colors.cardHeaderBg = '#fafafa';
            }
            
            // Try to get card background from actual card elements (override if found)
            const cardElement = parentDoc.querySelector('.card') ||
                               parentDoc.querySelector('[class*="card"]');
            
            if (cardElement) {
              const cardComputed = window.parent.getComputedStyle(cardElement);
              const cardBg = cardComputed.backgroundColor;
              if (cardBg && cardBg !== 'rgba(0, 0, 0, 0)' && cardBg !== 'transparent') {
                colors.cardBg = cardBg;
                colors.cardHeaderBg = cardBg;
              }
            }
          }
          
          // Get secondary text color from computed styles of muted text
          // Try multiple sources to find the actual secondary text color
          const mutedElements = [
            parentDoc.querySelector('[class*="muted"]'),
            parentDoc.querySelector('[class*="secondary"]'),
            parentDoc.querySelector('small'),
            parentDoc.querySelector('[class*="metadata"]'),
            parentDoc.querySelector('[class*="label"]'),
            parentDoc.querySelector('[class*="caption"]'),
            parentDoc.querySelector('[class*="helper"]')
          ].filter(el => el !== null);
          
          for (const mutedEl of mutedElements) {
            try {
              const mutedComputed = window.parent.getComputedStyle(mutedEl);
              const mutedColor = mutedComputed.color;
              if (mutedColor && 
                  mutedColor !== 'rgba(0, 0, 0, 0)' && 
                  mutedColor !== 'transparent' &&
                  mutedColor !== colors.textColor &&
                  mutedColor !== colors.bgColor) {
                colors.secondaryText = mutedColor;
                break;
              }
            } catch (e) {
              // Skip this element
            }
          }
          
          // Try to get text color from actual plugin content (like Scalars plugin)
          // Look for table cells, card text, or other content elements
          const textSampleElements = [
            parentDoc.querySelector('td'),
            parentDoc.querySelector('th'),
            parentDoc.querySelector('.card p'),
            parentDoc.querySelector('.card div'),
            parentDoc.querySelector('[class*="text"]'),
            parentDoc.querySelector('[class*="label"]'),
            contentElement
          ].filter(el => el !== null);
          
          // Find the first element with a valid text color
          for (const textEl of textSampleElements) {
            try {
              const textComputed = window.parent.getComputedStyle(textEl);
              const textColor = textComputed.color;
              // Make sure it's not transparent or the same as background
              if (textColor && 
                  textColor !== 'rgba(0, 0, 0, 0)' && 
                  textColor !== 'transparent' &&
                  textColor !== colors.bgColor &&
                  textColor !== colors.sidebarBg) {
                colors.textColor = textColor;
                break;
              }
            } catch (e) {
              // Skip this element
            }
          }
        }
      }
    } catch (e) {
      // Cross-origin or other error, use defaults
      console.log('Could not access parent theme:', e.message);
    }
    
    return colors;
  }
  
  // Helper to parse RGB color string
  function parseRgb(colorStr) {
    if (!colorStr) return null;
    const match = colorStr.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
    if (match) {
      return { r: parseInt(match[1]), g: parseInt(match[2]), b: parseInt(match[3]) };
    }
    // Try hex
    if (colorStr.startsWith('#')) {
      const hex = colorStr.slice(1);
      if (hex.length === 6) {
        return {
          r: parseInt(hex.slice(0, 2), 16),
          g: parseInt(hex.slice(2, 4), 16),
          b: parseInt(hex.slice(4, 6), 16)
        };
      }
    }
    return null;
  }
  
  // Helper to adjust brightness
  function adjustBrightness(colorStr, amount) {
    const rgb = parseRgb(colorStr);
    if (!rgb) return colorStr;
    const r = Math.max(0, Math.min(255, rgb.r + amount));
    const g = Math.max(0, Math.min(255, rgb.g + amount));
    const b = Math.max(0, Math.min(255, rgb.b + amount));
    return `rgb(${r}, ${g}, ${b})`;
  }
  
  const themeColors = getThemeColors();
  let bgColor = themeColors.bgColor;
  let textColor = themeColors.textColor;
  const fontFamily = themeColors.fontFamily;
  const fontSize = themeColors.fontSize;
  let borderColor = themeColors.borderColor;
  let hoverBg = themeColors.hoverBg;
  let headerBg = themeColors.headerBg;
  const evenRowBg = themeColors.evenRowBg;
  let cardBg = themeColors.cardBg;
  let cardHeaderBg = themeColors.cardHeaderBg;
  let sidebarBg = themeColors.sidebarBg;
  let secondaryText = themeColors.secondaryText;
  
  // Detect if dark theme for conditional logic
  const bgRgb = parseRgb(bgColor);
  let isDark = bgRgb ? (bgRgb.r + bgRgb.g + bgRgb.b) / 3 < 128 : true;
  
  // Theme-aware colors that respond to TensorBoard's theme toggle
  // All containers match sidebar background
  // These are let variables so they can be updated when theme changes
  let cardBackgroundColor = sidebarBg;
  // Main content background matches sidebar background
  let mainContentBackground = sidebarBg;
  let cardHeaderBackground = sidebarBg;
  // Use border color from TensorBoard instead of hardcoding
  let cardBorderColor = borderColor;
  // Use the actual text color from TensorBoard plugins instead of hardcoding
  let cardTextColor = textColor;
  let cardHeaderBorderColor = borderColor;
  let innerBoxBackground = sidebarBg;
  let innerBoxBorderColor = borderColor;
  let innerHeaderBackground = sidebarBg;
  
  // Compute active button background
  let activeBtnBg = adjustBrightness(hoverBg, isDark ? 10 : -10);
  
  // Function to update all theme colors dynamically
  function updateThemeColors() {
    // Declare all variables at the top to avoid any hoisting or scope issues
    const newThemeColors = getThemeColors();
    const newBgColor = newThemeColors.bgColor;
    const newTextColor = newThemeColors.textColor;
    const newSidebarBg = newThemeColors.sidebarBg;
    const newHeaderBg = newThemeColors.headerBg;
    const newHoverBg = newThemeColors.hoverBg;
    const newCardBg = newThemeColors.cardBg;
    const newCardHeaderBg = newThemeColors.cardHeaderBg;
    const newSecondaryText = newThemeColors.secondaryText;
    const newBgRgb = parseRgb(newBgColor);
    const newIsDark = newBgRgb ? (newBgRgb.r + newBgRgb.g + newBgRgb.b) / 3 < 128 : true;
    // Ensure borderColor is always defined with a fallback based on theme
    const newBorderColor = newThemeColors.borderColor || (newIsDark ? '#3c4043' : '#dadce0');
    const newActiveBtnBg = adjustBrightness(newHoverBg, newIsDark ? 10 : -10);
    // Use finalBorderColor consistently throughout the function
    const finalBorderColor = newBorderColor;
    
    // Update body styles
    document.body.style.background = newBgColor;
    document.body.style.color = newTextColor;
    
    // Update sidebar
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
      sidebar.style.background = newSidebarBg;
    }
    
    // Update sidebar header
    const sidebarHeader = document.querySelector('.sidebar-header');
    if (sidebarHeader) {
      sidebarHeader.style.color = newTextColor;
    }
    
    // Update main content - match sidebar background
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
      mainContent.style.background = newSidebarBg;
    }
    
    // Update all cards - match sidebar background, use border color from TensorBoard
    document.querySelectorAll('.card').forEach(card => {
      card.style.background = newSidebarBg;
      card.style.borderColor = finalBorderColor;
    });
    
    // Update all card headers - match sidebar background, use border color from TensorBoard
    document.querySelectorAll('.card-header').forEach(header => {
      header.style.background = newSidebarBg;
      header.style.borderBottomColor = finalBorderColor;
    });
    
    // Update card header titles - use actual text color from TensorBoard
    document.querySelectorAll('.card-header-title').forEach(title => {
      title.style.color = newTextColor;
    });
    
    // Update card header metadata - use secondary text color from TensorBoard
    document.querySelectorAll('.card-header-metadata').forEach(metadata => {
      metadata.style.color = newSecondaryText;
    });
    
    // Update card header chevrons - use secondary text color from TensorBoard
    document.querySelectorAll('.card-header-chevron').forEach(chevron => {
      chevron.style.color = newSecondaryText;
    });
    
    // Update search box
    const searchBox = document.querySelector('.search-box');
    if (searchBox) {
      searchBox.style.background = newSidebarBg;
      searchBox.style.color = newTextColor;
    }
    
    // Update sidebar buttons
    document.querySelectorAll('.sidebar-btn').forEach(btn => {
      btn.style.background = newSidebarBg;
      btn.style.color = newTextColor;
    });
    
    // Update run count
    const runCount = document.querySelector('.run-count');
    if (runCount) {
      runCount.style.color = newSecondaryText;
    }
    
    // Update run labels
    document.querySelectorAll('.run-label').forEach(label => {
      label.style.color = newTextColor;
    });
    
    // Update all run items (they might have been created dynamically)
    document.querySelectorAll('.run-item').forEach(item => {
      // Run items don't need background update, but ensure text is correct
      const label = item.querySelector('.run-label');
      if (label) {
        label.style.color = newTextColor;
      }
      // Always ensure run color boxes have their assigned colors
      const colorBox = item.querySelector('.run-color');
      if (colorBox && label) {
        const runName = label.textContent;
        const color = runColors.get(runName) || TENSORBOARD_COLORS[0];
        colorBox.style.backgroundColor = color;
        // Ensure the color box doesn't get overridden by theme updates
        colorBox.style.background = color;
      }
    });
    
    // Update chart action buttons - use secondary text color from TensorBoard
    document.querySelectorAll('.chart-action-btn').forEach(btn => {
      btn.style.color = newSecondaryText;
    });
    
    // Update inner content boxes - match sidebar background, use border color from TensorBoard
    document.querySelectorAll('.inner-content-box').forEach(box => {
      box.style.background = newSidebarBg;
      box.style.borderColor = finalBorderColor;
    });
    
    // Update inner content headers - match sidebar background, use secondary text color
    document.querySelectorAll('.inner-content-header').forEach(header => {
      header.style.background = newSidebarBg;
      header.style.borderBottomColor = finalBorderColor;
      header.style.color = newSecondaryText;
    });
    
    // Update table headers - match sidebar background, use actual text color
    document.querySelectorAll('th').forEach(th => {
      th.style.background = newSidebarBg;
      th.style.color = newTextColor;
    });
    
    // Update table cells - use actual text color from TensorBoard
    document.querySelectorAll('td').forEach(td => {
      td.style.color = newTextColor;
    });
    
    // Update run name cells specifically
    document.querySelectorAll('td.run-name').forEach(td => {
      td.style.color = newTextColor;
    });
    
    // Update tooltip - match sidebar background, use actual text color
    const tooltip = document.getElementById('tooltip');
    if (tooltip) {
      tooltip.style.background = newSidebarBg;
      tooltip.style.borderColor = finalBorderColor;
      tooltip.style.color = newTextColor;
    }
    
    // Update tooltip labels
    document.querySelectorAll('.tooltip-label').forEach(label => {
      label.style.color = newSecondaryText;
    });
    
    // Update tooltip values
    document.querySelectorAll('.tooltip-value').forEach(value => {
      value.style.color = newTextColor;
    });
    
    // Update tooltip title
    document.querySelectorAll('.tooltip-title').forEach(title => {
      title.style.color = newTextColor;
    });
    
    // Update chart backgrounds - match sidebar background
    document.querySelectorAll('.pareto-chart').forEach(chart => {
      chart.style.background = newSidebarBg;
    });
    
    // Update chart titles (any divs that are direct children of chart-wrapper)
    document.querySelectorAll('.chart-wrapper > div').forEach(div => {
      if (div.className === 'pareto-chart') {
        div.style.background = newSidebarBg;
      } else if (!div.classList.contains('chart-actions')) {
        // Likely a chart title - use actual text color
        div.style.color = newTextColor;
      }
    });
    
    // Update all SVG text elements in charts - these are created dynamically and need explicit updates
    document.querySelectorAll('svg text').forEach(textEl => {
      textEl.setAttribute('fill', newTextColor);
    });
    
    // Update all text elements inside chart containers
    document.querySelectorAll('.pareto-chart text').forEach(textEl => {
      textEl.setAttribute('fill', newTextColor);
    });
    
    // Update chart titles (divs with inline color styles) - these are created with inline styles
    document.querySelectorAll('.chart-wrapper > div').forEach(div => {
      const style = div.getAttribute('style') || '';
      if (style.includes('color:')) {
        // Replace any color value with the new text color
        const newStyle = style.replace(/color:\s*[^;]+/gi, 'color: ' + newTextColor);
        div.setAttribute('style', newStyle);
      }
    });
    
    // Update any divs with inline color styles inside charts
    document.querySelectorAll('.pareto-chart div[style*="color"]').forEach(div => {
      const style = div.getAttribute('style') || '';
      if (style.includes('color:')) {
        // Replace any color value with the new text color
        const newStyle = style.replace(/color:\s*[^;]+/gi, 'color: ' + newTextColor);
        div.setAttribute('style', newStyle);
      }
    });
    
    // Update all elements with inline style color (catch-all for any missed elements)
    document.querySelectorAll('[style*="color"]').forEach(el => {
      const style = el.getAttribute('style') || '';
      if (style.includes('color:')) {
        // Only update if it's not a background color or border color
        const colorMatch = style.match(/color:\s*([^;]+)/i);
        if (colorMatch) {
          const oldColor = colorMatch[1].trim();
          // Only update if it looks like a text color (not a background or border)
          if (!oldColor.includes('background') && !oldColor.includes('border')) {
            const newStyle = style.replace(/color:\s*[^;]+/gi, 'color: ' + newTextColor);
            el.setAttribute('style', newStyle);
          }
        }
      }
    });
    
    // Update loading text - use actual text color
    document.querySelectorAll('.loading').forEach(loading => {
      loading.style.color = newTextColor;
    });
    
      // Force update all dynamically created elements that might have been missed
      // This ensures any elements created between theme changes get updated
      requestAnimationFrame(() => {
        // Re-apply all updates to catch any newly created elements
        document.querySelectorAll('.card').forEach(card => {
          if (!card.style.background || card.style.background === '') {
            card.style.background = newSidebarBg;
            card.style.borderColor = finalBorderColor;
          }
        });
        
        document.querySelectorAll('.card-header-title').forEach(title => {
          if (!title.style.color || title.style.color === '') {
            title.style.color = newTextColor;
          }
        });
        
        document.querySelectorAll('td').forEach(td => {
          if (!td.style.color || td.style.color === '') {
            td.style.color = newTextColor;
          }
        });
        
        document.querySelectorAll('th').forEach(th => {
          if (!th.style.background || th.style.background === '') {
            th.style.background = newSidebarBg;
            th.style.color = newTextColor;
          }
        });
      });
    
    // Update the style tag by doing simple string replacements
    // Use split/join for simple string replacement (no regex needed)
    const styleEl = document.querySelector('style');
    if (styleEl) {
      let newStyleText = styleEl.textContent;
      
      // Ensure outer scope variables are initialized before using them
      const oldBgColor = typeof bgColor !== 'undefined' ? bgColor : newBgColor;
      const oldTextColor = typeof textColor !== 'undefined' ? textColor : newTextColor;
      const oldSidebarBg = typeof sidebarBg !== 'undefined' ? sidebarBg : newSidebarBg;
      const oldHeaderBg = typeof headerBg !== 'undefined' ? headerBg : newHeaderBg;
      const oldHoverBg = typeof hoverBg !== 'undefined' ? hoverBg : newHoverBg;
      const oldCardBg = typeof cardBg !== 'undefined' ? cardBg : newCardBg;
      const oldCardHeaderBg = typeof cardHeaderBg !== 'undefined' ? cardHeaderBg : newCardHeaderBg;
      const oldSecondaryText = typeof secondaryText !== 'undefined' ? secondaryText : newSecondaryText;
      const oldActiveBtnBg = typeof activeBtnBg !== 'undefined' ? activeBtnBg : newActiveBtnBg;
      const oldIsDark = typeof isDark !== 'undefined' ? isDark : newIsDark;
      
      // Replace all color values using simple string replacement
      // This avoids regex escaping issues
      if (oldBgColor !== newBgColor) {
        newStyleText = newStyleText.split(oldBgColor).join(newBgColor);
      }
      if (oldTextColor !== newTextColor) {
        newStyleText = newStyleText.split(oldTextColor).join(newTextColor);
      }
      if (oldSidebarBg !== newSidebarBg) {
        newStyleText = newStyleText.split(oldSidebarBg).join(newSidebarBg);
      }
      if (oldHeaderBg !== newHeaderBg) {
        newStyleText = newStyleText.split(oldHeaderBg).join(newHeaderBg);
      }
      if (oldHoverBg !== newHoverBg) {
        newStyleText = newStyleText.split(oldHoverBg).join(newHoverBg);
      }
      if (oldCardBg !== newCardBg) {
        newStyleText = newStyleText.split(oldCardBg).join(newCardBg);
      }
      if (oldCardHeaderBg !== newCardHeaderBg) {
        newStyleText = newStyleText.split(oldCardHeaderBg).join(newCardHeaderBg);
      }
      if (oldSecondaryText !== newSecondaryText) {
        newStyleText = newStyleText.split(oldSecondaryText).join(newSecondaryText);
      }
      if (oldActiveBtnBg !== newActiveBtnBg) {
        newStyleText = newStyleText.split(oldActiveBtnBg).join(newActiveBtnBg);
      }
      
      // Replace main content background (now matches sidebar)
      // The CSS uses ${sidebarBg}, so it will be updated via sidebarBg replacement above
      
      // Replace card backgrounds
      const oldCardBgValue = oldIsDark ? '#303134' : '#ffffff';
      const newCardBgValue = newIsDark ? '#303134' : '#ffffff';
      if (oldCardBgValue !== newCardBgValue) {
        newStyleText = newStyleText.split(oldCardBgValue).join(newCardBgValue);
      }
      
      // Replace card header backgrounds
      const oldCardHeaderBgValue = oldIsDark ? '#2d2e31' : '#ffffff';
      const newCardHeaderBgValue = newIsDark ? '#2d2e31' : '#ffffff';
      if (oldCardHeaderBgValue !== newCardHeaderBgValue) {
        newStyleText = newStyleText.split(oldCardHeaderBgValue).join(newCardHeaderBgValue);
      }
      
      // Replace card border colors
      const oldCardBorder = oldIsDark ? '#3c4043' : '#dadce0';
      const newCardBorder = newIsDark ? '#3c4043' : '#dadce0';
      if (oldCardBorder !== newCardBorder) {
        newStyleText = newStyleText.split(oldCardBorder).join(newCardBorder);
      }
      
      // Replace inner box backgrounds
      const oldInnerBoxBg = oldIsDark ? '#2d2e31' : '#ffffff';
      const newInnerBoxBg = newIsDark ? '#2d2e31' : '#ffffff';
      if (oldInnerBoxBg !== newInnerBoxBg) {
        newStyleText = newStyleText.split(oldInnerBoxBg).join(newInnerBoxBg);
      }
      
      // Replace inner box border colors
      const oldInnerBoxBorder = oldIsDark ? '#3c4043' : '#dadce0';
      const newInnerBoxBorder = newIsDark ? '#3c4043' : '#dadce0';
      if (oldInnerBoxBorder !== newInnerBoxBorder) {
        newStyleText = newStyleText.split(oldInnerBoxBorder).join(newInnerBoxBorder);
      }
      
      // Replace inner header backgrounds
      const oldInnerHeaderBg = oldIsDark ? '#353638' : '#fafafa';
      const newInnerHeaderBg = newIsDark ? '#353638' : '#fafafa';
      if (oldInnerHeaderBg !== newInnerHeaderBg) {
        newStyleText = newStyleText.split(oldInnerHeaderBg).join(newInnerHeaderBg);
      }
      
      // Replace card header border colors
      const oldCardHeaderBorder = oldIsDark ? '#3c4043' : '#dadce0';
      const newCardHeaderBorder = newIsDark ? '#3c4043' : '#dadce0';
      if (oldCardHeaderBorder !== newCardHeaderBorder) {
        newStyleText = newStyleText.split(oldCardHeaderBorder).join(newCardHeaderBorder);
      }
      
      // Replace card text colors
      const oldCardText = oldIsDark ? '#e8eaed' : '#3c4043';
      const newCardText = newIsDark ? '#e8eaed' : '#3c4043';
      if (oldCardText !== newCardText) {
        newStyleText = newStyleText.split(oldCardText).join(newCardText);
      }
      
      // Replace table row hover colors (was inverted!)
      const oldTrHover = oldIsDark ? '#3c4043' : '#f1f3f4';
      const newTrHover = newIsDark ? '#3c4043' : '#f1f3f4';
      if (oldTrHover !== newTrHover) {
        newStyleText = newStyleText.split(oldTrHover).join(newTrHover);
      }
      
      // Replace card header hover colors
      const oldCardHeaderHover = oldIsDark ? '#353638' : '#f8f9fa';
      const newCardHeaderHover = newIsDark ? '#353638' : '#f8f9fa';
      if (oldCardHeaderHover !== newCardHeaderHover) {
        newStyleText = newStyleText.split(oldCardHeaderHover).join(newCardHeaderHover);
      }
      
      // Replace chart action button colors in CSS
      const oldChartBtnColor = oldIsDark ? '#9aa0a6' : '#5f6368';
      const newChartBtnColor = newIsDark ? '#9aa0a6' : '#5f6368';
      if (oldChartBtnColor !== newChartBtnColor) {
        newStyleText = newStyleText.split(oldChartBtnColor).join(newChartBtnColor);
      }
      
      // Replace chart action button hover backgrounds
      const oldChartBtnHover = oldIsDark ? '#3c4043' : '#f1f3f4';
      const newChartBtnHover = newIsDark ? '#3c4043' : '#f1f3f4';
      if (oldChartBtnHover !== newChartBtnHover) {
        newStyleText = newStyleText.split(oldChartBtnHover).join(newChartBtnHover);
      }
      
      // Replace inner content header text colors in CSS
      const oldInnerHeaderText = oldIsDark ? '#5f6368' : '#80868b';
      const newInnerHeaderText = newIsDark ? '#9aa0a6' : '#80868b';
      if (oldInnerHeaderText !== newInnerHeaderText) {
        newStyleText = newStyleText.split(oldInnerHeaderText).join(newInnerHeaderText);
      }
      
      // Replace card header metadata colors in CSS
      const oldMetadataColor = oldIsDark ? '#9aa0a6' : '#80868b';
      const newMetadataColor = newIsDark ? '#9aa0a6' : '#80868b';
      if (oldMetadataColor !== newMetadataColor) {
        newStyleText = newStyleText.split(oldMetadataColor).join(newMetadataColor);
      }
      
      // Replace card header chevron colors in CSS
      const oldChevronColor = oldIsDark ? '#5f6368' : '#80868b';
      const newChevronColor = newIsDark ? '#9aa0a6' : '#80868b';
      if (oldChevronColor !== newChevronColor) {
        newStyleText = newStyleText.split(oldChevronColor).join(newChevronColor);
      }
      
      styleEl.textContent = newStyleText;
      
      // Update global variables for future reference
      bgColor = newBgColor;
      textColor = newTextColor;
      sidebarBg = newSidebarBg;
      headerBg = newHeaderBg;
      hoverBg = newHoverBg;
      cardBg = newCardBg;
      cardHeaderBg = newCardHeaderBg;
      secondaryText = newSecondaryText;
      borderColor = finalBorderColor;
      activeBtnBg = newActiveBtnBg;
      isDark = newIsDark;
      
      // Update theme-aware color variables - all containers match sidebar
      cardBackgroundColor = newSidebarBg;
      mainContentBackground = newSidebarBg;
      cardHeaderBackground = newSidebarBg;
      cardBorderColor = finalBorderColor;
      // Use the actual text color from TensorBoard plugins
      cardTextColor = newTextColor;
      cardHeaderBorderColor = finalBorderColor;
      innerBoxBackground = newSidebarBg;
      innerBoxBorderColor = finalBorderColor;
      innerHeaderBackground = newSidebarBg;
    }
  }
  
  // Set up theme change detection
  function setupThemeChangeListener() {
    try {
      if (window.parent && window.parent !== window) {
        const parentBody = window.parent.document.body;
        if (parentBody) {
          // Use MutationObserver to watch for style/class changes on parent body
          const observer = new MutationObserver((mutations) => {
            let shouldUpdate = false;
            mutations.forEach((mutation) => {
              if (mutation.type === 'attributes' && 
                  (mutation.attributeName === 'style' || mutation.attributeName === 'class')) {
                shouldUpdate = true;
              }
            });
            if (shouldUpdate) {
              // Debounce updates
              clearTimeout(window.themeUpdateTimeout);
              window.themeUpdateTimeout = setTimeout(() => {
                updateThemeColors();
              }, 100);
            }
          });
          
          observer.observe(parentBody, {
            attributes: true,
            attributeFilter: ['style', 'class'],
            subtree: false
          });
          
          // Also watch for changes in computed styles by polling (as fallback)
          let lastBgColor = window.parent.getComputedStyle(parentBody).backgroundColor;
          setInterval(() => {
            try {
              const currentBgColor = window.parent.getComputedStyle(parentBody).backgroundColor;
              if (currentBgColor !== lastBgColor) {
                lastBgColor = currentBgColor;
                updateThemeColors();
              }
            } catch (e) {
              // Ignore cross-origin errors
            }
          }, 500); // Check every 500ms
        }
      }
    } catch (e) {
      console.log('Could not set up theme change listener:', e.message);
    }
  }
  
  // TensorBoard's standard color palette for runs
  const TENSORBOARD_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d3', '#c7c7c7', '#dbdb8d', '#9edae5'
  ];
  
  // Set up HTML structure with sidebar matching TensorBoard's SCALARS plugin
  document.body.innerHTML = `
    <style>
      body {
        font-family: ${fontFamily};
        font-size: ${fontSize};
        margin: 0;
        padding: 0;
        background: ${bgColor};
        color: ${textColor};
        display: flex;
        height: 100vh;
        overflow: hidden;
      }
      .sidebar {
        width: 280px;
        background: ${sidebarBg};
        overflow-y: auto;
        flex-shrink: 0;
        padding: 16px;
      }
      .sidebar-header {
        font-size: 13px;
        font-weight: 500;
        color: ${textColor};
        margin-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      .search-box {
        width: 100%;
        padding: 6px 8px;
        margin-bottom: 12px;
        background: ${sidebarBg};
        border: none;
        border-radius: 2px;
        color: ${textColor};
        font-family: ${fontFamily};
        font-size: ${fontSize};
      }
      .search-box:focus {
        outline: none;
      }
      .sidebar-controls {
        display: flex;
        gap: 6px;
        margin-bottom: 12px;
      }
      .sidebar-btn {
        flex: 1;
        padding: 6px 8px;
        background: ${sidebarBg};
        border: none;
        border-radius: 2px;
        color: ${textColor};
        font-family: ${fontFamily};
        font-size: 12px;
        cursor: pointer;
        text-align: center;
      }
      .sidebar-btn:hover {
        background: ${hoverBg} !important;
      }
      .run-count {
        font-size: 12px;
        color: ${secondaryText};
        margin-bottom: 8px;
      }
      .run-item {
        display: flex;
        align-items: center;
        padding: 6px 8px;
        margin: 2px 0;
        cursor: pointer;
        border-radius: 2px;
        user-select: none;
      }
      .run-item:hover {
        background: ${hoverBg} !important;
      }
      .run-item input[type="checkbox"] {
        margin-right: 8px;
        cursor: pointer;
      }
      .run-color {
        width: 12px;
        height: 12px;
        border-radius: 2px;
        margin-right: 8px;
        flex-shrink: 0;
        border: none;
      }
      .run-label {
        flex: 1;
        font-size: ${fontSize};
        color: ${textColor};
        cursor: pointer;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .run-item.disabled .run-label {
        opacity: 0.5;
      }
      .main-content {
        flex: 1;
        padding: 20px;
        overflow-y: auto;
        background: ${sidebarBg};
      }
      .content-column {
        max-width: 1200px;
        margin: 0 auto;
      }
      .charts-grid {
        display: flex;
        flex-direction: column;
        gap: 20px;
        margin-bottom: 20px;
      }
      .chart-card {
        width: 100%;
      }
      .chart-card .inner-content-body {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
      }
      .chart-wrapper {
        grid-column: span 1;
      }
      .chart-wrapper.expanded {
        grid-column: span 3;
      }
      .chart-actions {
        display: flex;
        gap: 8px;
        margin-top: 8px;
        justify-content: flex-end;
      }
      .chart-action-btn {
        width: 24px;
        height: 24px;
        border: none;
        background: transparent;
        color: ${secondaryText};
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 2px;
        font-size: 16px;
        padding: 0;
      }
      .chart-action-btn:hover {
        background: ${hoverBg} !important;
        color: ${textColor} !important;
      }
      .chart-action-btn:active {
        background: ${hoverBg};
        opacity: 0.8;
      }
      .card {
        background: ${sidebarBg};
        border: 1px solid ${cardBorderColor};
        border-radius: 4px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
        margin-bottom: 20px;
        overflow: hidden;
      }
      .card-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        border-bottom: 1px solid ${cardHeaderBorderColor};
        background: ${sidebarBg};
        cursor: pointer;
        user-select: none;
      }
      .card-header:hover {
        background: ${hoverBg} !important;
      }
      .card-header-title {
        font-size: 14px;
        font-weight: 500;
        color: ${textColor};
        flex: 1;
      }
      .card-header-metadata {
        font-size: 12px;
        color: ${secondaryText};
        margin-top: 4px;
        font-weight: 400;
      }
      .card-header-tag {
        font-size: 11px;
        color: ${secondaryText};
        background: ${hoverBg};
        padding: 2px 8px;
        border-radius: 10px;
        margin-right: 8px;
      }
      .card-header-chevron {
        font-size: 12px;
        color: ${secondaryText};
        transition: transform 0.2s;
        margin-left: 8px;
      }
      .card-header-chevron.collapsed {
        transform: rotate(-90deg);
      }
      .card-content {
        padding: 0;
        display: block;
      }
      .card-content.collapsed {
        display: none;
      }
      .inner-content-box {
        background: ${sidebarBg};
        border: 1px solid ${innerBoxBorderColor};
        border-radius: 2px;
        margin: 16px 20px;
        overflow: hidden;
      }
      .inner-content-header {
        padding: 8px 12px;
        background: ${sidebarBg};
        border-bottom: 1px solid ${innerBoxBorderColor};
        font-size: 12px;
        font-weight: 500;
        color: ${secondaryText};
      }
      .inner-content-body {
        padding: 16px;
      }
      #paretoContainer {
        display: none;
      }
      .pareto-chart {
        width: 100%;
        min-height: 300px;
        height: 300px;
        background: ${sidebarBg};
        position: relative;
      }
      .chart-card.expanded .pareto-chart {
        min-height: 400px;
        height: 400px;
      }
      .pareto-chart svg {
        width: 100%;
        height: 100%;
        display: block;
      }
      table {
        border-collapse: collapse;
        width: 100%;
        font-size: ${fontSize};
        font-family: ${fontFamily};
      }
      th, td {
        border-bottom: none;
        padding: 8px 12px;
        text-align: right;
      }
      th {
        background: ${sidebarBg};
        font-weight: 500;
        color: ${textColor};
        position: sticky;
        top: 0;
        z-index: 10;
        cursor: pointer;
        user-select: none;
      }
      th.sortable::after {
        content: ' ↕';
        opacity: 0.5;
      }
      th.sort-asc::after {
        content: ' ↑';
        opacity: 1;
      }
      th.sort-desc::after {
        content: ' ↓';
        opacity: 1;
      }
      tbody tr:hover {
        background: ${hoverBg} !important;
      }
      td {
        color: ${textColor};
      }
      .run-name {
        text-align: left;
        font-weight: 500;
      }
      .loading {
        text-align: center;
        padding: 40px;
        color: ${textColor};
      }
      .tooltip {
        position: absolute;
        background: ${sidebarBg};
        opacity: 0.95;
        border: 1px solid ${cardBorderColor};
        border-radius: 4px;
        padding: 12px;
        font-size: ${fontSize};
        font-family: ${fontFamily};
        color: ${textColor};
        pointer-events: none;
        z-index: 1000;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        max-width: 300px;
        display: none;
      }
      .tooltip-title {
        font-weight: 500;
        margin-bottom: 8px;
        font-size: 13px;
      }
      .tooltip-row {
        display: flex;
        justify-content: space-between;
        margin: 4px 0;
        font-size: 12px;
      }
      .tooltip-label {
        color: ${secondaryText};
        margin-right: 12px;
      }
      .tooltip-value {
        font-weight: 500;
      }
    </style>
    <div class="sidebar">
      <div class="sidebar-header">Runs</div>
      <input type="text" class="search-box" id="searchBox" placeholder="Search runs...">
      <div class="sidebar-controls">
        <button class="sidebar-btn" id="selectAllBtn">Select All</button>
        <button class="sidebar-btn" id="deselectAllBtn">Deselect All</button>
      </div>
      <div class="run-count" id="runCount"></div>
      <div id="runList"></div>
    </div>
    <div class="main-content">
      <div id="tooltip" class="tooltip"></div>
      <div class="content-column">
        <div id="chartsGrid" class="charts-grid" style="display: none;"></div>
        <div id="root">
          <div class="loading">Loading compression data...</div>
        </div>
      </div>
    </div>
  `;
  
  // State management
  let allRuns = [];
  let runColors = new Map();
  let visibleRuns = new Set();
  let searchTerm = '';
  let sortColumn = null;
  let sortDirection = 'asc';
  
  // Format helpers
  const formatVal = (val) => val !== null && val !== undefined ? val.toFixed(4) : '-';
  const formatRatio = (val) => val !== null && val !== undefined ? val.toFixed(2) + 'x' : '-';
  
  // Assign colors to runs (TensorBoard style)
  function assignRunColors() {
    allRuns.forEach((run, index) => {
      const color = TENSORBOARD_COLORS[index % TENSORBOARD_COLORS.length];
      runColors.set(run.run, color);
    });
  }
  
  // Render sidebar with run checkboxes
  function renderSidebar() {
    const runList = document.getElementById('runList');
    const runCountEl = document.getElementById('runCount');
    runList.innerHTML = '';
    
    // Filter runs by search term
    const filteredRuns = allRuns.filter(run => 
      run.run.toLowerCase().includes(searchTerm.toLowerCase())
    );
    
    filteredRuns.forEach(run => {
      const color = runColors.get(run.run) || TENSORBOARD_COLORS[0];
      const isVisible = visibleRuns.has(run.run);
      
      const item = document.createElement('div');
      item.className = 'run-item' + (isVisible ? '' : ' disabled');
      
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.checked = isVisible;
      checkbox.addEventListener('change', (e) => {
        if (e.target.checked) {
          visibleRuns.add(run.run);
        } else {
          visibleRuns.delete(run.run);
        }
        updateRunCount();
        render();
      });
      
      const colorBox = document.createElement('div');
      colorBox.className = 'run-color';
      colorBox.style.backgroundColor = color;
      
      const label = document.createElement('label');
      label.className = 'run-label';
      label.textContent = run.run;
      label.addEventListener('click', (e) => {
        e.preventDefault();
        checkbox.checked = !checkbox.checked;
        checkbox.dispatchEvent(new Event('change'));
      });
      
      item.appendChild(checkbox);
      item.appendChild(colorBox);
      item.appendChild(label);
      runList.appendChild(item);
    });
    
    updateRunCount();
  }
  
  // Update run count display
  function updateRunCount() {
    const runCountEl = document.getElementById('runCount');
    const visibleCount = visibleRuns.size;
    const totalCount = allRuns.length;
    runCountEl.textContent = visibleCount + ' of ' + totalCount + ' runs';
  }
  
  // Render table and charts
  function render() {
    let runs = allRuns.filter(r => visibleRuns.has(r.run));
    
    // Calculate ratios for sorting
    runs = runs.map(r => {
      const accuracyRatio = calculateRatio(r.accuracy_fp32, r.accuracy_int8);
      const latencyRatio = r.speedup !== null && r.speedup !== undefined ? r.speedup : calculateRatio(r.latency_fp32, r.latency_int8);
      const energyRatio = calculateRatio(r.energy_fp32, r.energy_int8);
      const sizeRatio = r.size_ratio !== null && r.size_ratio !== undefined ? r.size_ratio : calculateRatio(r.model_size_fp32, r.model_size_int8);
      return {
        ...r,
        accuracy_ratio: accuracyRatio,
        latency_ratio: latencyRatio,
        energy_ratio: energyRatio,
        size_ratio: sizeRatio
      };
    });
    
    // Sort if needed
    if (sortColumn) {
      runs.sort((a, b) => {
        let aVal = a[sortColumn];
        let bVal = b[sortColumn];
        if (aVal === null || aVal === undefined) aVal = -Infinity;
        if (bVal === null || bVal === undefined) bVal = -Infinity;
        const comparison = aVal > bVal ? 1 : aVal < bVal ? -1 : 0;
        return sortDirection === 'asc' ? comparison : -comparison;
      });
    }
    
    renderChartsGrid(runs);
    renderRelativeMetricsTable(runs);
    renderRawMetricsTable(runs);
    
    // Update theme colors after rendering to ensure new elements have correct colors
    // Use setTimeout to ensure DOM is updated first
    setTimeout(() => {
      updateThemeColors();
    }, 0);
  }
  
  // Calculate ratio values
  function calculateRatio(fp32, int8) {
    if (fp32 === null || fp32 === undefined || int8 === null || int8 === undefined || int8 === 0) {
      return null;
    }
    return fp32 / int8;
  }
  
  // Render charts in a three-column grid
  function renderChartsGrid(runs) {
    if (!runs || runs.length === 0) {
      document.getElementById('chartsGrid').style.display = 'none';
      return;
    }
    
    const grid = document.getElementById('chartsGrid');
    grid.style.display = 'flex';
    grid.innerHTML = '';
    
    // Create the Pareto Frontier View card with multiple charts
    const chartCard = document.createElement('div');
    chartCard.className = 'card chart-card';
    chartCard.id = 'paretoChartCard';
    
    const cardHeader = document.createElement('div');
    cardHeader.className = 'card-header';
    const headerContent = document.createElement('div');
    headerContent.style.cssText = 'flex: 1;';
    const titleDiv = document.createElement('div');
    titleDiv.className = 'card-header-title';
    titleDiv.textContent = 'Pareto Frontier View';
    const metadataDiv = document.createElement('div');
    metadataDiv.className = 'card-header-metadata';
    metadataDiv.textContent = 'compression/pareto';
    headerContent.appendChild(titleDiv);
    headerContent.appendChild(metadataDiv);
    const chevronDiv = document.createElement('div');
    chevronDiv.className = 'card-header-chevron';
    chevronDiv.textContent = '▼';
    cardHeader.appendChild(headerContent);
    cardHeader.appendChild(chevronDiv);
    
    const cardContent = document.createElement('div');
    cardContent.className = 'card-content';
    
    const innerBox = document.createElement('div');
    innerBox.className = 'inner-content-box';
    
    const innerHeader = document.createElement('div');
    innerHeader.className = 'inner-content-header';
    innerHeader.textContent = 'Accuracy vs Compression Metrics';
    
    const innerBody = document.createElement('div');
    innerBody.className = 'inner-content-body';
    
    // Create multiple charts: Accuracy vs Model Size, Latency, Memory, Energy
    const chartConfigs = [
      { id: 'paretoChart', title: 'Accuracy vs Model Size', xKey: 'model_size', xLabel: 'Model Size (MB)' },
      { id: 'latencyChart', title: 'Accuracy vs Latency', xKey: 'latency', xLabel: 'Latency (ms)' },
      { id: 'memoryChart', title: 'Accuracy vs Memory Usage', xKey: 'memory', xLabel: 'Memory Usage (MB)' },
      { id: 'energyChart', title: 'Accuracy vs Energy Consumption', xKey: 'energy', xLabel: 'Energy (mW)' }
    ];
    
    // Note: For now, we only have model_size data. Latency, memory, and energy charts will show "No data available"
    // until those metrics are added to the backend data extraction
    
    chartConfigs.forEach((config, index) => {
      const chartWrapper = document.createElement('div');
      chartWrapper.className = 'chart-wrapper';
      chartWrapper.id = config.id + 'Wrapper';
      
      const chartTitle = document.createElement('div');
      chartTitle.style.cssText = 'font-size: 12px; font-weight: 500; margin-bottom: 8px; color: ' + textColor + ';';
      chartTitle.textContent = config.title;
      
      const chartDiv = document.createElement('div');
      chartDiv.className = 'pareto-chart';
      chartDiv.id = config.id;
      chartDiv.setAttribute('data-x-key', config.xKey);
      chartDiv.setAttribute('data-x-label', config.xLabel);
      
      const actionsDiv = document.createElement('div');
      actionsDiv.className = 'chart-actions';
      
      const expandBtn = document.createElement('button');
      expandBtn.className = 'chart-action-btn';
      expandBtn.title = 'Expand chart to full width';
      expandBtn.innerHTML = '⛶';
      expandBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isExpanded = chartWrapper.classList.contains('expanded');
        if (isExpanded) {
          chartWrapper.classList.remove('expanded');
          expandBtn.title = 'Expand chart to full width';
        } else {
          // Collapse other expanded charts
          document.querySelectorAll('.chart-wrapper.expanded').forEach(w => {
            w.classList.remove('expanded');
          });
          chartWrapper.classList.add('expanded');
          expandBtn.title = 'Collapse chart to normal size';
        }
        // Re-render chart to adjust to new size
        setTimeout(() => renderParetoChart(runs, config.id, config.xKey, config.xLabel), 150);
      });
      
      const downloadBtn = document.createElement('button');
      downloadBtn.className = 'chart-action-btn';
      downloadBtn.title = 'Download as SVG';
      downloadBtn.innerHTML = '⬇';
      downloadBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        downloadChartAsSVG(config.id, config.title);
      });
      
      actionsDiv.appendChild(expandBtn);
      actionsDiv.appendChild(downloadBtn);
      
      chartWrapper.appendChild(chartTitle);
      chartWrapper.appendChild(chartDiv);
      chartWrapper.appendChild(actionsDiv);
      innerBody.appendChild(chartWrapper);
    });
    
    innerBox.appendChild(innerHeader);
    innerBox.appendChild(innerBody);
    cardContent.appendChild(innerBox);
    
    cardHeader.addEventListener('click', () => {
      cardContent.classList.toggle('collapsed');
      const chevron = cardHeader.querySelector('.card-header-chevron');
      chevron.classList.toggle('collapsed');
    });
    
    chartCard.appendChild(cardHeader);
    chartCard.appendChild(cardContent);
    grid.appendChild(chartCard);
    
    // Render all charts
    setTimeout(() => {
      chartConfigs.forEach(config => {
        renderParetoChart(runs, config.id, config.xKey, config.xLabel);
      });
    }, 10);
  }
  
  // Download chart as SVG
  function downloadChartAsSVG(chartId, chartTitle) {
    const chartDiv = document.getElementById(chartId);
    if (!chartDiv) return;
    
    const svg = chartDiv.querySelector('svg');
    if (!svg) {
      alert('No chart available to download');
      return;
    }
    
    // Clone the SVG to avoid modifying the original
    const svgClone = svg.cloneNode(true);
    
    // Get SVG as string
    const svgData = new XMLSerializer().serializeToString(svgClone);
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const svgUrl = URL.createObjectURL(svgBlob);
    
    const downloadLink = document.createElement('a');
    downloadLink.href = svgUrl;
    downloadLink.download = (chartTitle || 'chart').toLowerCase().replace(/\s+/g, '_') + '.svg';
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
    URL.revokeObjectURL(svgUrl);
  }
  
  // Render Pareto chart (Accuracy vs various metrics)
  function renderParetoChart(runs, chartId, xKey, xLabel) {
    if (!runs || runs.length === 0) {
      return;
    }
    
    const chart = document.getElementById(chartId);
    if (!chart) {
      console.error('Chart container not found:', chartId);
      return;
    }
    
    // Wait a tick to ensure container is laid out
    setTimeout(() => {
      renderChartWithD3(runs, chart, xKey, xLabel);
    }, 10);
  }
  
  function renderChartWithD3(runs, chart, xKey, xLabelParam) {
    xKey = xKey || 'model_size';
    const xLabel = xLabelParam || 'Model Size (MB)';
    
    // Prepare data based on xKey: X = metric (model_size, latency, memory, energy), Y = Accuracy
    // Separate FP32 and INT8 points, assign colors
    const fp32Data = [];
    const int8Data = [];
    
    // Map xKey to data field names
    const xKeyMap = {
      'model_size': { fp32: 'model_size_fp32', int8: 'model_size_int8' },
      'latency': { fp32: 'latency_fp32', int8: 'latency_int8' },
      'memory': { fp32: 'memory_fp32', int8: 'memory_int8' },
      'energy': { fp32: 'energy_fp32', int8: 'energy_int8' }
    };
    
    const fields = xKeyMap[xKey] || xKeyMap['model_size'];
    
    runs.forEach(r => {
      const runColor = runColors.get(r.run) || TENSORBOARD_COLORS[0];
      const xFp32 = r[fields.fp32];
      const xInt8 = r[fields.int8];
      
      if (xFp32 !== null && xFp32 !== undefined && 
          r.accuracy_fp32 !== null && r.accuracy_fp32 !== undefined) {
        fp32Data.push({
          run: r.run,
          x: xFp32,
          y: r.accuracy_fp32,
          color: runColor,
          type: 'FP32',
          fullData: r
        });
      }
      if (xInt8 !== null && xInt8 !== undefined && 
          r.accuracy_int8 !== null && r.accuracy_int8 !== undefined) {
        int8Data.push({
          run: r.run,
          x: xInt8,
          y: r.accuracy_int8,
          color: runColor,
          type: 'INT8',
          fullData: r
        });
      }
    });
    
    if (fp32Data.length === 0 && int8Data.length === 0) {
      chart.innerHTML = '<div style="padding: 40px; text-align: center; color: ' + cardTextColor + ';">No data available for chart</div>';
      return;
    }
    
    console.log('Rendering chart with', fp32Data.length, 'FP32 points and', int8Data.length, 'INT8 points');
    
    // Try multiple ways to access D3 from TensorBoard
    let d3 = null;
    
    // Method 1: Try parent window
    try {
      if (window.parent && window.parent !== window) {
        if (window.parent.d3) {
          d3 = window.parent.d3;
          console.log('Using D3 from parent window');
        } else if (window.parent.window && window.parent.window.d3) {
          d3 = window.parent.window.d3;
          console.log('Using D3 from parent.window');
        }
      }
    } catch (e) {
      console.log('Cannot access parent window:', e.message);
    }
    
    // Method 2: Try top window
    try {
      if (window.top && window.top !== window && !d3) {
        if (window.top.d3) {
          d3 = window.top.d3;
          console.log('Using D3 from top window');
        }
      }
    } catch (e) {
      // Cross-origin
    }
    
    // Method 3: Try to find D3 in global scope via iframe
    if (!d3) {
      try {
        const frames = window.parent.frames;
        for (let i = 0; i < frames.length; i++) {
          try {
            if (frames[i].d3) {
              d3 = frames[i].d3;
              console.log('Using D3 from frame', i);
              break;
            }
          } catch (e) {
            // Skip cross-origin frames
          }
        }
      } catch (e) {
        // Cannot access frames
      }
    }
    
    // If still no D3, use native SVG approach
    if (!d3) {
      console.log('D3 not available, using native SVG');
      createNativeSVGChart(chart, fp32Data, int8Data, cardTextColor, fontFamily, sidebarBg, borderColor, formatVal, formatRatio, xLabel);
      return;
    }
    
    createChart(d3, chart, fp32Data, int8Data, cardTextColor, fontFamily, sidebarBg, borderColor, formatVal, formatRatio, xLabel);
    
    function createChart(d3, chart, fp32Data, int8Data, textColor, fontFamily, bgColor, borderColor, formatVal, formatRatio, xLabelParam) {
      const xLabel = xLabelParam || 'Model Size (MB)';
      const tooltip = document.getElementById('tooltip');
      
      function showTooltip(event, d) {
        const r = d.fullData;
        const html = '<div class="tooltip-title">' + d.run + ' (' + d.type + ')</div>' +
          '<div class="tooltip-row"><span class="tooltip-label">Accuracy:</span><span class="tooltip-value">' + formatVal(d.y) + '</span></div>' +
          '<div class="tooltip-row"><span class="tooltip-label">Model Size:</span><span class="tooltip-value">' + d.x.toFixed(2) + ' MB</span></div>' +
          (r.accuracy_drop !== null && r.accuracy_drop !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Accuracy Drop:</span><span class="tooltip-value">' + formatVal(r.accuracy_drop) + '</span></div>' : '') +
          (r.size_ratio !== null && r.size_ratio !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Size Ratio:</span><span class="tooltip-value">' + formatRatio(r.size_ratio) + '</span></div>' : '') +
          (r.speedup !== null && r.speedup !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Speedup:</span><span class="tooltip-value">' + formatRatio(r.speedup) + '</span></div>' : '') +
          (r.memory_reduction_mb !== null && r.memory_reduction_mb !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Memory Reduction:</span><span class="tooltip-value">' + formatVal(r.memory_reduction_mb) + ' MB</span></div>' : '') +
          (r.energy_reduction_mw !== null && r.energy_reduction_mw !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Energy Reduction:</span><span class="tooltip-value">' + formatVal(r.energy_reduction_mw) + ' mW</span></div>' : '');
        
        tooltip.innerHTML = html;
        tooltip.style.display = 'block';
        
        const rect = chart.getBoundingClientRect();
        const x = event.pageX - rect.left;
        const y = event.pageY - rect.top;
        
        tooltip.style.left = (x + 15) + 'px';
        tooltip.style.top = (y - 10) + 'px';
        
        // Adjust if tooltip goes off screen
        const tooltipRect = tooltip.getBoundingClientRect();
        if (tooltipRect.right > window.innerWidth) {
          tooltip.style.left = (x - tooltipRect.width - 15) + 'px';
        }
        if (tooltipRect.bottom > window.innerHeight) {
          tooltip.style.top = (y - tooltipRect.height - 10) + 'px';
        }
      }
      
      function hideTooltip() {
        tooltip.style.display = 'none';
      }
      if (!d3) {
        chart.innerHTML = '<div style="padding: 40px; text-align: center; color: ' + textColor + ';">D3.js not available</div>';
        return;
      }
      
      // Clear previous chart
      chart.innerHTML = '';
      
      // Ensure chart container has dimensions
      if (chart.offsetWidth === 0 || chart.offsetHeight === 0) {
        chart.style.width = '100%';
        chart.style.height = '400px';
      }
      
      // Chart dimensions
      const width = chart.offsetWidth || 800;
      const height = chart.offsetHeight || 400;
      const margin = { top: 20, right: 20, bottom: 50, left: 70 };
      const plotWidth = width - margin.left - margin.right;
      const plotHeight = height - margin.top - margin.bottom;
      
      // Calculate bounds for all data
      const allX = [...fp32Data.map(d => d.x), ...int8Data.map(d => d.x)];
      const allY = [...fp32Data.map(d => d.y), ...int8Data.map(d => d.y)];
      
      if (allX.length === 0 || allY.length === 0) {
        chart.innerHTML = '<div style="padding: 40px; text-align: center; color: ' + textColor + ';">No data points to display</div>';
        return;
      }
      
      const xMin = Math.min(...allX);
      const xMax = Math.max(...allX);
      const yMin = Math.min(...allY);
      const yMax = Math.max(...allY);
      
      // Add padding
      const xRange = xMax - xMin || 1;
      const yRange = yMax - yMin || 1;
      const xPadding = xRange * 0.1;
      const yPadding = yRange * 0.1;
      const xScaleMin = Math.max(0, xMin - xPadding);
      const xScaleMax = xMax + xPadding;
      const yScaleMin = Math.max(0, yMin - yPadding);
      const yScaleMax = Math.min(1, yMax + yPadding);
      
      // Create SVG with explicit viewBox for responsiveness
      const svg = d3.select(chart)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', '0 0 ' + width + ' ' + height)
        .style('display', 'block');
      
      const g = svg.append('g')
        .attr('transform', 'translate(' + margin.left + ',' + margin.top + ')');
      
      // Create scales (D3 way)
      const xScale = d3.scaleLinear()
        .domain([xScaleMin, xScaleMax])
        .range([0, plotWidth]);
      
      const yScale = d3.scaleLinear()
        .domain([yScaleMin, yScaleMax])
        .range([plotHeight, 0]);
      
      // Create axes
      const xAxis = d3.axisBottom(xScale).ticks(8);
      const yAxis = d3.axisLeft(yScale).ticks(8);
      
      // Add grid lines
      g.append('g')
        .attr('class', 'grid')
        .attr('transform', 'translate(0,' + plotHeight + ')')
        .call(xAxis.tickSize(-plotHeight).tickFormat(''))
        .selectAll('line')
        .attr('stroke', 'none')
        .attr('stroke-width', 0)
        .attr('stroke-dasharray', '2,2')
        .attr('opacity', 0);
      
      g.append('g')
        .attr('class', 'grid')
        .call(yAxis.tickSize(-plotWidth).tickFormat(''))
        .selectAll('line')
        .attr('stroke', 'none')
        .attr('stroke-width', 0)
        .attr('stroke-dasharray', '2,2')
        .attr('opacity', 0);
      
      // Add axes
      g.append('g')
        .attr('class', 'axis')
        .attr('transform', 'translate(0,' + plotHeight + ')')
        .call(xAxis)
        .selectAll('text')
        .style('fill', textColor)
        .style('font-family', fontFamily)
        .style('font-size', '11px');
      
      g.append('g')
        .attr('class', 'axis')
        .call(yAxis)
        .selectAll('text')
        .style('fill', textColor)
        .style('font-family', fontFamily)
        .style('font-size', '11px');
      
      // Style axes
      g.selectAll('.axis line, .axis path')
        .attr('stroke', borderColor)
        .attr('stroke-width', 1);
      
      g.selectAll('.axis .tick line')
        .attr('stroke', borderColor)
        .attr('stroke-width', 1);
      
      // Add axis labels
      g.append('text')
        .attr('transform', 'translate(' + (plotWidth / 2) + ',' + (plotHeight + margin.bottom - 5) + ')')
        .style('text-anchor', 'middle')
        .style('fill', textColor)
        .style('font-family', fontFamily)
        .style('font-size', '12px')
        .text(xLabel);
      
      g.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('y', -margin.left + 15)
        .attr('x', -plotHeight / 2)
        .style('text-anchor', 'middle')
        .style('fill', textColor)
        .style('font-family', fontFamily)
        .style('font-size', '12px')
        .text('Accuracy');
      
      // Create triangle marker for FP32
      const triangleSize = 6;
      const trianglePath = d3.symbol().type(d3.symbolTriangle).size(triangleSize * 10);
      
      // Create square marker for INT8
      const squareSize = 5;
      const squarePath = d3.symbol().type(d3.symbolSquare).size(squareSize * 10);
      
      // Add FP32 points (triangles) with run colors
      if (fp32Data.length > 0) {
        g.selectAll('.fp32-point')
          .data(fp32Data)
          .enter()
          .append('path')
          .attr('class', 'fp32-point')
          .attr('d', trianglePath)
          .attr('transform', d => 'translate(' + xScale(d.x) + ',' + yScale(d.y) + ')')
          .attr('fill', d => d.color || '#4285f4')
          .attr('stroke', bgColor)
          .attr('stroke-width', 1)
          .style('cursor', 'pointer')
          .on('mouseover', function(event, d) {
            d3.select(this).attr('transform', 'translate(' + xScale(d.x) + ',' + yScale(d.y) + ') scale(1.2)');
            showTooltip(event, d);
          })
          .on('mousemove', function(event, d) {
            showTooltip(event, d);
          })
          .on('mouseout', function(event, d) {
            d3.select(this).attr('transform', 'translate(' + xScale(d.x) + ',' + yScale(d.y) + ')');
            hideTooltip();
          });
      }
      
      // Add INT8 points (squares) with run colors
      if (int8Data.length > 0) {
        g.selectAll('.int8-point')
          .data(int8Data)
          .enter()
          .append('path')
          .attr('class', 'int8-point')
          .attr('d', squarePath)
          .attr('transform', d => 'translate(' + xScale(d.x) + ',' + yScale(d.y) + ')')
          .attr('fill', d => d.color || '#ea4335')
          .attr('stroke', 'none')
          .attr('stroke-width', 0)
          .style('cursor', 'pointer')
          .on('mouseover', function(event, d) {
            d3.select(this).attr('transform', 'translate(' + xScale(d.x) + ',' + yScale(d.y) + ') scale(1.2)');
            showTooltip(event, d);
          })
          .on('mousemove', function(event, d) {
            showTooltip(event, d);
          })
          .on('mouseout', function(event, d) {
            d3.select(this).attr('transform', 'translate(' + xScale(d.x) + ',' + yScale(d.y) + ')');
            hideTooltip();
          });
      }
      
      // Add legend
      const legend = g.append('g')
        .attr('class', 'legend')
        .attr('transform', 'translate(' + (plotWidth - 100) + ', 10)');
      
      if (fp32Data.length > 0) {
        const fp32Legend = legend.append('g');
        fp32Legend.append('path')
          .attr('d', trianglePath)
          .attr('fill', '#4285f4')
          .attr('stroke', 'none')
          .attr('stroke-width', 0);
        fp32Legend.append('text')
          .attr('x', 15)
          .attr('y', 4)
          .style('fill', textColor)
          .style('font-family', fontFamily)
          .style('font-size', '11px')
          .text('FP32');
      }
      
      if (int8Data.length > 0) {
        const int8Legend = legend.append('g')
          .attr('transform', 'translate(0, 20)');
        int8Legend.append('path')
          .attr('d', squarePath)
          .attr('fill', '#ea4335')
          .attr('stroke', 'none')
          .attr('stroke-width', 0);
        int8Legend.append('text')
          .attr('x', 15)
          .attr('y', 4)
          .style('fill', textColor)
          .style('font-family', fontFamily)
          .style('font-size', '11px')
          .text('INT8');
      }
    }
  }
  
  // Native SVG chart (fallback when D3 not available)
  function createNativeSVGChart(chart, fp32Data, int8Data, textColor, fontFamily, bgColor, borderColor, formatVal, formatRatio, xLabelParam) {
    const xLabel = xLabelParam || 'Model Size (MB)';
    const tooltip = document.getElementById('tooltip');
    
    function showTooltip(event, d) {
      const r = d.fullData;
      const html = '<div class="tooltip-title">' + d.run + ' (' + d.type + ')</div>' +
        '<div class="tooltip-row"><span class="tooltip-label">Accuracy:</span><span class="tooltip-value">' + formatVal(d.y) + '</span></div>' +
        '<div class="tooltip-row"><span class="tooltip-label">Model Size:</span><span class="tooltip-value">' + d.x.toFixed(2) + ' MB</span></div>' +
        (r.accuracy_drop !== null && r.accuracy_drop !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Accuracy Drop:</span><span class="tooltip-value">' + formatVal(r.accuracy_drop) + '</span></div>' : '') +
        (r.size_ratio !== null && r.size_ratio !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Size Ratio:</span><span class="tooltip-value">' + formatRatio(r.size_ratio) + '</span></div>' : '') +
        (r.speedup !== null && r.speedup !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Speedup:</span><span class="tooltip-value">' + formatRatio(r.speedup) + '</span></div>' : '') +
        (r.memory_reduction_mb !== null && r.memory_reduction_mb !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Memory Reduction:</span><span class="tooltip-value">' + formatVal(r.memory_reduction_mb) + ' MB</span></div>' : '') +
        (r.energy_reduction_mw !== null && r.energy_reduction_mw !== undefined ? '<div class="tooltip-row"><span class="tooltip-label">Energy Reduction:</span><span class="tooltip-value">' + formatVal(r.energy_reduction_mw) + ' mW</span></div>' : '');
      
      tooltip.innerHTML = html;
      tooltip.style.display = 'block';
      
      const rect = chart.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      
      tooltip.style.left = (x + 15) + 'px';
      tooltip.style.top = (y - 10) + 'px';
      
      // Adjust if tooltip goes off screen
      setTimeout(() => {
        const tooltipRect = tooltip.getBoundingClientRect();
        if (tooltipRect.right > window.innerWidth) {
          tooltip.style.left = (x - tooltipRect.width - 15) + 'px';
        }
        if (tooltipRect.bottom > window.innerHeight) {
          tooltip.style.top = (y - tooltipRect.height - 10) + 'px';
        }
      }, 0);
    }
    
    function hideTooltip() {
      tooltip.style.display = 'none';
    }
    // Clear previous chart
    chart.innerHTML = '';
    
    // Ensure chart container has dimensions
    if (chart.offsetWidth === 0 || chart.offsetHeight === 0) {
      chart.style.width = '100%';
      chart.style.height = '400px';
    }
    
    const width = chart.offsetWidth || 800;
    const height = chart.offsetHeight || 400;
    const margin = { top: 20, right: 20, bottom: 50, left: 70 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    
    // Calculate bounds
    const allX = [...fp32Data.map(d => d.x), ...int8Data.map(d => d.x)];
    const allY = [...fp32Data.map(d => d.y), ...int8Data.map(d => d.y)];
    
    if (allX.length === 0 || allY.length === 0) {
      // Use cardTextColor from outer scope (passed as textColor parameter)
      chart.innerHTML = '<div style="padding: 40px; text-align: center; color: ' + textColor + ';">No data points to display</div>';
      return;
    }
    
    const xMin = Math.min(...allX);
    const xMax = Math.max(...allX);
    const yMin = Math.min(...allY);
    const yMax = Math.max(...allY);
    
    // Add padding
    const xRange = xMax - xMin || 1;
    const yRange = yMax - yMin || 1;
    const xPadding = xRange * 0.1;
    const yPadding = yRange * 0.1;
    const xScaleMin = Math.max(0, xMin - xPadding);
    const xScaleMax = xMax + xPadding;
    const yScaleMin = Math.max(0, yMin - yPadding);
    const yScaleMax = Math.min(1, yMax + yPadding);
    
    // Scale functions
    const scaleX = (val) => margin.left + ((val - xScaleMin) / (xScaleMax - xScaleMin)) * plotWidth;
    const scaleY = (val) => margin.top + plotHeight - ((val - yScaleMin) / (yScaleMax - yScaleMin)) * plotHeight;
    
    // Create SVG
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('width', width);
    svg.setAttribute('height', height);
    svg.style.display = 'block';
    
    // Add grid lines
    const gridLines = 8;
    for (let i = 0; i <= gridLines; i++) {
      const xVal = xScaleMin + (xScaleMax - xScaleMin) * (i / gridLines);
      const x = scaleX(xVal);
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', x);
      line.setAttribute('y1', margin.top);
      line.setAttribute('x2', x);
      line.setAttribute('y2', height - margin.bottom);
      line.setAttribute('stroke', borderColor);
      line.setAttribute('stroke-width', 0.5);
      line.setAttribute('stroke-dasharray', '2,2');
      line.setAttribute('opacity', '0.3');
      svg.appendChild(line);
    }
    
    for (let i = 0; i <= gridLines; i++) {
      const yVal = yScaleMin + (yScaleMax - yScaleMin) * (i / gridLines);
      const y = scaleY(yVal);
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', margin.left);
      line.setAttribute('y1', y);
      line.setAttribute('x2', width - margin.right);
      line.setAttribute('y2', y);
      line.setAttribute('stroke', borderColor);
      line.setAttribute('stroke-width', 0.5);
      line.setAttribute('stroke-dasharray', '2,2');
      line.setAttribute('opacity', '0.3');
      svg.appendChild(line);
    }
    
    // Add axes
    const xAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    xAxis.setAttribute('x1', margin.left);
    xAxis.setAttribute('y1', height - margin.bottom);
    xAxis.setAttribute('x2', width - margin.right);
    xAxis.setAttribute('y2', height - margin.bottom);
    xAxis.setAttribute('stroke', 'none');
    xAxis.setAttribute('stroke-width', 0);
    svg.appendChild(xAxis);
    
    const yAxis = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    yAxis.setAttribute('x1', margin.left);
    yAxis.setAttribute('y1', margin.top);
    yAxis.setAttribute('x2', margin.left);
    yAxis.setAttribute('y2', height - margin.bottom);
    yAxis.setAttribute('stroke', 'none');
    yAxis.setAttribute('stroke-width', 0);
    svg.appendChild(yAxis);
    
    // Add axis labels and ticks
    for (let i = 0; i <= gridLines; i++) {
      const xVal = xScaleMin + (xScaleMax - xScaleMin) * (i / gridLines);
      const x = scaleX(xVal);
      const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      tick.setAttribute('x1', x);
      tick.setAttribute('y1', height - margin.bottom);
      tick.setAttribute('x2', x);
      tick.setAttribute('y2', height - margin.bottom + 5);
      tick.setAttribute('stroke', 'none');
      tick.setAttribute('stroke-width', 0);
      svg.appendChild(tick);
      
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', x);
      label.setAttribute('y', height - margin.bottom + 20);
      label.setAttribute('text-anchor', 'middle');
      label.setAttribute('fill', textColor);
      label.setAttribute('font-family', fontFamily);
      label.setAttribute('font-size', '11px');
      label.textContent = xVal.toFixed(1);
      svg.appendChild(label);
    }
    
    for (let i = 0; i <= gridLines; i++) {
      const yVal = yScaleMin + (yScaleMax - yScaleMin) * (i / gridLines);
      const y = scaleY(yVal);
      const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      tick.setAttribute('x1', margin.left);
      tick.setAttribute('y1', y);
      tick.setAttribute('x2', margin.left - 5);
      tick.setAttribute('y2', y);
      tick.setAttribute('stroke', 'none');
      tick.setAttribute('stroke-width', 0);
      svg.appendChild(tick);
      
      const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      label.setAttribute('x', margin.left - 10);
      label.setAttribute('y', y + 4);
      label.setAttribute('text-anchor', 'end');
      label.setAttribute('fill', textColor);
      label.setAttribute('font-family', fontFamily);
      label.setAttribute('font-size', '11px');
      label.textContent = yVal.toFixed(3);
      svg.appendChild(label);
    }
    
    // Add axis titles
    const xLabelEl = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    xLabelEl.setAttribute('x', width / 2);
    xLabelEl.setAttribute('y', height - 5);
    xLabelEl.setAttribute('text-anchor', 'middle');
    xLabelEl.setAttribute('fill', textColor);
    xLabelEl.setAttribute('font-family', fontFamily);
    xLabelEl.setAttribute('font-size', '12px');
    xLabelEl.textContent = xLabel || 'Model Size (MB)';
    svg.appendChild(xLabelEl);
    
    const yLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    yLabel.setAttribute('x', margin.left / 2);
    yLabel.setAttribute('y', height / 2);
    yLabel.setAttribute('text-anchor', 'middle');
    yLabel.setAttribute('fill', textColor);
    yLabel.setAttribute('font-family', fontFamily);
    yLabel.setAttribute('font-size', '12px');
    yLabel.setAttribute('transform', 'rotate(-90, ' + (margin.left / 2) + ', ' + (height / 2) + ')');
    yLabel.textContent = 'Accuracy';
    svg.appendChild(yLabel);
    
    // Add FP32 points (triangles) with run colors
    fp32Data.forEach(d => {
      const x = scaleX(d.x);
      const y = scaleY(d.y);
      const runColor = d.color || TENSORBOARD_COLORS[0];
      const triangle = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      const size = 6;
      const points = [
        x + ',' + (y - size),
        (x - size * 0.866) + ',' + (y + size * 0.5),
        (x + size * 0.866) + ',' + (y + size * 0.5)
      ].join(' ');
      triangle.setAttribute('points', points);
      triangle.setAttribute('fill', runColor);
      triangle.setAttribute('stroke', 'none');
      triangle.setAttribute('stroke-width', 0);
      triangle.style.cursor = 'pointer';
      triangle.addEventListener('mouseenter', (e) => showTooltip(e, d));
      triangle.addEventListener('mousemove', (e) => showTooltip(e, d));
      triangle.addEventListener('mouseleave', hideTooltip);
      svg.appendChild(triangle);
    });
    
    // Add INT8 points (squares) with run colors
    int8Data.forEach(d => {
      const x = scaleX(d.x);
      const y = scaleY(d.y);
      const runColor = d.color || TENSORBOARD_COLORS[0];
      const square = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      const size = 5;
      square.setAttribute('x', x - size / 2);
      square.setAttribute('y', y - size / 2);
      square.setAttribute('width', size);
      square.setAttribute('height', size);
      square.setAttribute('fill', runColor);
      square.setAttribute('stroke', 'none');
      square.setAttribute('stroke-width', 0);
      square.style.cursor = 'pointer';
      square.addEventListener('mouseenter', (e) => showTooltip(e, d));
      square.addEventListener('mousemove', (e) => showTooltip(e, d));
      square.addEventListener('mouseleave', hideTooltip);
      svg.appendChild(square);
    });
    
    // Add legend
    const legendY = 30;
    if (fp32Data.length > 0) {
      const fp32Triangle = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      const size = 6;
      const points = [
        (width - 100) + ',' + (legendY - size),
        (width - 100 - size * 0.866) + ',' + (legendY + size * 0.5),
        (width - 100 + size * 0.866) + ',' + (legendY + size * 0.5)
      ].join(' ');
      fp32Triangle.setAttribute('points', points);
      fp32Triangle.setAttribute('fill', '#4285f4');
      fp32Triangle.setAttribute('stroke', 'none');
      fp32Triangle.setAttribute('stroke-width', 0);
      svg.appendChild(fp32Triangle);
      
      const fp32Text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      fp32Text.setAttribute('x', width - 85);
      fp32Text.setAttribute('y', legendY + 4);
      fp32Text.setAttribute('fill', textColor);
      fp32Text.setAttribute('font-family', fontFamily);
      fp32Text.setAttribute('font-size', '11px');
      fp32Text.textContent = 'FP32';
      svg.appendChild(fp32Text);
    }
    
    if (int8Data.length > 0) {
      const int8Square = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      const size = 5;
      int8Square.setAttribute('x', width - 100 - size / 2);
      int8Square.setAttribute('y', legendY + 20 - size / 2);
      int8Square.setAttribute('width', size);
      int8Square.setAttribute('height', size);
      int8Square.setAttribute('fill', '#ea4335');
      int8Square.setAttribute('stroke', 'none');
      int8Square.setAttribute('stroke-width', 0);
      svg.appendChild(int8Square);
      
      const int8Text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      int8Text.setAttribute('x', width - 85);
      int8Text.setAttribute('y', legendY + 24);
      int8Text.setAttribute('fill', textColor);
      int8Text.setAttribute('font-family', fontFamily);
      int8Text.setAttribute('font-size', '11px');
      int8Text.textContent = 'INT8';
      svg.appendChild(int8Text);
    }
    
    chart.appendChild(svg);
  }
  
  // Export to CSV
  function exportToCSV() {
    const visibleRunsData = allRuns.filter(r => visibleRuns.has(r.run));
    if (visibleRunsData.length === 0) {
      alert('No runs selected to export');
      return;
    }
    
    const headers = ['Run', 'FP32 Acc', 'INT8 Acc', 'Accuracy Drop', 'Size Ratio', 'Speedup', 'Memory Reduction (MB)', 'Energy Reduction (mW)', 'Model Size FP32 (MB)', 'Model Size INT8 (MB)'];
    const rows = visibleRunsData.map(r => [
      r.run,
      r.accuracy_fp32 !== null && r.accuracy_fp32 !== undefined ? r.accuracy_fp32.toFixed(4) : '',
      r.accuracy_int8 !== null && r.accuracy_int8 !== undefined ? r.accuracy_int8.toFixed(4) : '',
      r.accuracy_drop !== null && r.accuracy_drop !== undefined ? r.accuracy_drop.toFixed(4) : '',
      r.size_ratio !== null && r.size_ratio !== undefined ? r.size_ratio.toFixed(2) : '',
      r.speedup !== null && r.speedup !== undefined ? r.speedup.toFixed(2) : '',
      r.memory_reduction_mb !== null && r.memory_reduction_mb !== undefined ? r.memory_reduction_mb.toFixed(4) : '',
      r.energy_reduction_mw !== null && r.energy_reduction_mw !== undefined ? r.energy_reduction_mw.toFixed(4) : '',
      r.model_size_fp32 !== null && r.model_size_fp32 !== undefined ? r.model_size_fp32.toFixed(2) : '',
      r.model_size_int8 !== null && r.model_size_int8 !== undefined ? r.model_size_int8.toFixed(2) : ''
    ]);
    
    const csvContent = [headers, ...rows].map(row => 
      row.map(cell => '"' + String(cell).replace(/"/g, '""') + '"').join(',')
    ).join('\\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'compression_data.csv';
    link.click();
  }
  
  // Calculate ratio values
  function calculateRatio(fp32, int8) {
    if (fp32 === null || fp32 === undefined || int8 === null || int8 === undefined || int8 === 0) {
      return null;
    }
    return fp32 / int8;
  }
  
  // Render relative metrics table (ratios)
  function renderRelativeMetricsTable(runs) {
    const root = document.getElementById('root');
    if (!runs || runs.length === 0) {
      return;
    }
    
    let html = '<div class="card" id="relativeMetricsCard"><div class="card-header" id="relativeMetricsCardHeader"><div style="flex: 1;"><div class="card-header-title">Relative Metrics Table</div><div class="card-header-metadata">compression/relative_metrics</div></div><div class="card-header-chevron" id="relativeMetricsChevron">▼</div></div><div class="card-content" id="relativeMetricsCardContent"><div class="inner-content-box"><div class="inner-content-header">Ratios (FP32 / INT8)</div><div class="inner-content-body"><div class="table-container"><table><thead><tr>';
    const columns = [
      { key: 'run', label: 'Run', class: 'run-name sortable' },
      { key: 'accuracy_ratio', label: 'Accuracy Ratio', class: 'sortable' },
      { key: 'latency_ratio', label: 'Latency Ratio', class: 'sortable' },
      { key: 'energy_ratio', label: 'Energy Ratio', class: 'sortable' },
      { key: 'size_ratio', label: 'Size Ratio', class: 'sortable' }
    ];
    
    columns.forEach(col => {
      let className = col.class || '';
      if (sortColumn === col.key) {
        className += ' sort-' + sortDirection;
      }
      html += '<th class="' + className + '" data-column="' + col.key + '">' + col.label + '</th>';
    });
    html += '</tr></thead><tbody>';
    
    runs.forEach(r => {
      html += '<tr>' +
        '<td class="run-name">' + r.run + '</td>' +
        '<td>' + formatRatio(r.accuracy_ratio) + '</td>' +
        '<td>' + formatRatio(r.latency_ratio) + '</td>' +
        '<td>' + formatRatio(r.energy_ratio) + '</td>' +
        '<td>' + formatRatio(r.size_ratio) + '</td>' +
        '</tr>';
    });
    html += '</tbody></table></div></div></div></div></div>';
    
    // Replace or append relative metrics table
    const existingRelative = root.querySelector('#relativeMetricsCard');
    if (existingRelative) {
      existingRelative.outerHTML = html;
    } else {
      root.insertAdjacentHTML('beforeend', html);
    }
    
    // Add sort handlers
    document.querySelectorAll('#relativeMetricsCardContent th.sortable').forEach(th => {
      th.addEventListener('click', () => {
        const column = th.getAttribute('data-column');
        if (sortColumn === column) {
          sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
          sortColumn = column;
          sortDirection = 'asc';
        }
        render();
      });
    });
    
    // Add collapse handlers
    const relativeMetricsCardHeader = document.getElementById('relativeMetricsCardHeader');
    const relativeMetricsCardContent = document.getElementById('relativeMetricsCardContent');
    const relativeMetricsChevron = document.getElementById('relativeMetricsChevron');
    if (relativeMetricsCardHeader && relativeMetricsCardContent && relativeMetricsChevron) {
      relativeMetricsCardHeader.addEventListener('click', () => {
        const isCollapsed = relativeMetricsCardContent.classList.contains('collapsed');
        if (isCollapsed) {
          relativeMetricsCardContent.classList.remove('collapsed');
          relativeMetricsChevron.classList.remove('collapsed');
        } else {
          relativeMetricsCardContent.classList.add('collapsed');
          relativeMetricsChevron.classList.add('collapsed');
        }
      });
    }
  }
  
  // Render raw metrics table
  function renderRawMetricsTable(runs) {
    const root = document.getElementById('root');
    if (!runs || runs.length === 0) {
      return;
    }
    
    let html = '<div class="card" id="rawMetricsCard"><div class="card-header" id="rawMetricsCardHeader"><div style="flex: 1;"><div class="card-header-title">Raw Metrics Table</div><div class="card-header-metadata">compression/raw_metrics</div></div><div class="card-header-chevron" id="rawMetricsChevron">▼</div></div><div class="card-content" id="rawMetricsCardContent"><div class="inner-content-box"><div class="inner-content-header">Raw Values</div><div class="inner-content-body"><div class="table-container"><table><thead><tr>';
    const columns = [
      { key: 'run', label: 'Run', class: 'run-name sortable' },
      { key: 'accuracy_fp32', label: 'FP32 Accuracy', class: 'sortable' },
      { key: 'accuracy_int8', label: 'INT8 Accuracy', class: 'sortable' },
      { key: 'latency_fp32', label: 'FP32 Latency (ms)', class: 'sortable' },
      { key: 'latency_int8', label: 'INT8 Latency (ms)', class: 'sortable' },
      { key: 'energy_fp32', label: 'FP32 Energy (mW)', class: 'sortable' },
      { key: 'energy_int8', label: 'INT8 Energy (mW)', class: 'sortable' },
      { key: 'model_size_fp32', label: 'FP32 Size (MB)', class: 'sortable' },
      { key: 'model_size_int8', label: 'INT8 Size (MB)', class: 'sortable' }
    ];
    
    columns.forEach(col => {
      let className = col.class || '';
      if (sortColumn === col.key) {
        className += ' sort-' + sortDirection;
      }
      html += '<th class="' + className + '" data-column="' + col.key + '">' + col.label + '</th>';
    });
    html += '</tr></thead><tbody>';
    
    runs.forEach(r => {
      html += '<tr>' +
        '<td class="run-name">' + r.run + '</td>' +
        '<td>' + formatVal(r.accuracy_fp32) + '</td>' +
        '<td>' + formatVal(r.accuracy_int8) + '</td>' +
        '<td>' + formatVal(r.latency_fp32) + '</td>' +
        '<td>' + formatVal(r.latency_int8) + '</td>' +
        '<td>' + formatVal(r.energy_fp32) + '</td>' +
        '<td>' + formatVal(r.energy_int8) + '</td>' +
        '<td>' + formatVal(r.model_size_fp32) + '</td>' +
        '<td>' + formatVal(r.model_size_int8) + '</td>' +
        '</tr>';
    });
    html += '</tbody></table></div></div></div></div></div>';
    
    // Replace or append raw metrics table
    const existingRaw = root.querySelector('#rawMetricsCard');
    if (existingRaw) {
      existingRaw.outerHTML = html;
    } else {
      root.insertAdjacentHTML('beforeend', html);
    }
    
    // Add sort handlers
    document.querySelectorAll('#rawMetricsCardContent th.sortable').forEach(th => {
      th.addEventListener('click', () => {
        const column = th.getAttribute('data-column');
        if (sortColumn === column) {
          sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
          sortColumn = column;
          sortDirection = 'asc';
        }
        render();
      });
    });
    
    // Add collapse handlers
    const rawMetricsCardHeader = document.getElementById('rawMetricsCardHeader');
    const rawMetricsCardContent = document.getElementById('rawMetricsCardContent');
    const rawMetricsChevron = document.getElementById('rawMetricsChevron');
    if (rawMetricsCardHeader && rawMetricsCardContent && rawMetricsChevron) {
      rawMetricsCardHeader.addEventListener('click', () => {
        const isCollapsed = rawMetricsCardContent.classList.contains('collapsed');
        if (isCollapsed) {
          rawMetricsCardContent.classList.remove('collapsed');
          rawMetricsChevron.classList.remove('collapsed');
        } else {
          rawMetricsCardContent.classList.add('collapsed');
          rawMetricsChevron.classList.add('collapsed');
        }
      });
    }
  }
  
  // Fetch data and render
  const apiUrl = '/data/plugin/compression/api/summary';
  fetch(apiUrl)
    .then(r => {
      if (!r.ok) {
        throw new Error('HTTP ' + r.status + ': ' + r.statusText);
      }
      return r.json();
    })
    .then(data => {
      if (!data.runs || data.runs.length === 0) {
        document.getElementById('root').textContent = 'No compression data found.';
        return;
      }
      
      allRuns = data.runs;
      // Initially show all runs
      allRuns.forEach(run => visibleRuns.add(run.run));
      
      // Clear loading message
      const root = document.getElementById('root');
      root.innerHTML = '';
      
      assignRunColors();
      renderSidebar();
      render();
      
      // Set up theme change listener
      setupThemeChangeListener();
      
      // Update theme colors initially to ensure correct colors on first load
      updateThemeColors();
      
      // Search box handler
      const searchBox = document.getElementById('searchBox');
      searchBox.addEventListener('input', (e) => {
        searchTerm = e.target.value;
        renderSidebar();
      });
      
      // Select All / Deselect All buttons
      document.getElementById('selectAllBtn').addEventListener('click', () => {
        allRuns.forEach(run => visibleRuns.add(run.run));
        renderSidebar();
        render();
      });
      
      document.getElementById('deselectAllBtn').addEventListener('click', () => {
        visibleRuns.clear();
        renderSidebar();
        render();
      });
      
    })
    .catch(e => {
      console.error('Error:', e);
      const root = document.getElementById('root');
      root.innerHTML = '<div class="card"><div class="card-content"><div class="inner-content-box"><div class="inner-content-body" style="text-align: center; padding: 40px; color: ' + textColor + ';">Error: ' + e.message + '</div></div></div></div>';
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
</head>
<body>
  <div>This endpoint is not used. The plugin loads via ES module.</div>
</body>
</html>"""
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
                        "model_size_fp32": get_scalar("performance/model_size_mb/fp32"),
                        "model_size_int8": get_scalar("performance/model_size_mb/int8"),
                        "latency_fp32": get_scalar("performance/latency_ms/fp32") or get_scalar("performance/latency/fp32"),
                        "latency_int8": get_scalar("performance/latency_ms/int8") or get_scalar("performance/latency/int8"),
                        "memory_fp32": get_scalar("performance/memory_usage_mb/fp32") or get_scalar("performance/memory_usage/fp32"),
                        "memory_int8": get_scalar("performance/memory_usage_mb/int8") or get_scalar("performance/memory_usage/int8"),
                        "energy_fp32": get_scalar("performance/energy_mw/fp32") or get_scalar("performance/energy_consumption_mw/fp32") or get_scalar("performance/energy/fp32"),
                        "energy_int8": get_scalar("performance/energy_mw/int8") or get_scalar("performance/energy_consumption_mw/int8") or get_scalar("performance/energy/int8"),
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
                            "model_size_fp32": get_scalar("performance/model_size_mb/fp32"),
                            "model_size_int8": get_scalar("performance/model_size_mb/int8"),
                            "latency_fp32": get_scalar("performance/latency_ms/fp32") or get_scalar("performance/latency/fp32"),
                            "latency_int8": get_scalar("performance/latency_ms/int8") or get_scalar("performance/latency/int8"),
                            "memory_fp32": get_scalar("performance/memory_usage_mb/fp32") or get_scalar("performance/memory_usage/fp32"),
                            "memory_int8": get_scalar("performance/memory_usage_mb/int8") or get_scalar("performance/memory_usage/int8"),
                            "energy_fp32": get_scalar("performance/energy_mw/fp32") or get_scalar("performance/energy_consumption_mw/fp32") or get_scalar("performance/energy/fp32"),
                            "energy_int8": get_scalar("performance/energy_mw/int8") or get_scalar("performance/energy_consumption_mw/int8") or get_scalar("performance/energy/int8"),
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
