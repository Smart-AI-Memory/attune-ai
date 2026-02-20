"""CSS and JavaScript Assets for Socratic Web UI

Provides static CSS styles and JavaScript for form interactivity,
plus a helper function to retrieve both as a bundle.

Copyright 2026 Smart-AI-Memory
Licensed under the Apache License, Version 2.0
"""

from __future__ import annotations

# =============================================================================
# CSS STYLES
# =============================================================================


FORM_CSS = """
/* Socratic Form Styles */

.socratic-form {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.form-header {
  margin-bottom: 2rem;
}

.form-header h2 {
  margin: 0 0 0.5rem 0;
  font-size: 1.75rem;
  color: #1a1a2e;
}

.form-description {
  color: #666;
  margin: 0 0 1rem 0;
}

.progress-bar {
  background: #e0e0e0;
  border-radius: 10px;
  height: 20px;
  position: relative;
  overflow: hidden;
}

.progress-fill {
  background: linear-gradient(90deg, #4CAF50, #8BC34A);
  height: 100%;
  border-radius: 10px;
  transition: width 0.3s ease;
}

.progress-text {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.75rem;
  font-weight: 600;
  color: #333;
}

.form-fields {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-field {
  background: #f8f9fa;
  padding: 1.25rem;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.form-field label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #1a1a2e;
}

.form-field .required {
  color: #e53935;
  margin-left: 0.25rem;
}

.help-text {
  font-size: 0.875rem;
  color: #666;
  margin: 0 0 0.75rem 0;
}

/* Text inputs */
input[type="text"],
input[type="number"],
textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 1rem;
  transition: border-color 0.2s, box-shadow 0.2s;
}

input[type="text"]:focus,
input[type="number"]:focus,
textarea:focus {
  outline: none;
  border-color: #4CAF50;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

textarea {
  min-height: 100px;
  resize: vertical;
}

/* Radio and checkbox groups */
.radio-group,
.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.radio-option,
.checkbox-option {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.75rem;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.radio-option:hover,
.checkbox-option:hover {
  border-color: #4CAF50;
  background: #f0f7f0;
}

.radio-option.recommended,
.checkbox-option.recommended {
  border-color: #4CAF50;
}

.radio-option input,
.checkbox-option input {
  margin-top: 0.25rem;
}

.option-label {
  font-weight: 500;
  color: #1a1a2e;
}

.option-desc {
  display: block;
  font-size: 0.875rem;
  color: #666;
  margin-top: 0.25rem;
}

/* Switch/toggle */
.switch-container {
  display: flex;
  align-items: center;
}

.switch {
  position: relative;
  width: 50px;
  height: 28px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.switch .slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  border-radius: 28px;
  transition: 0.3s;
}

.switch .slider:before {
  position: absolute;
  content: "";
  height: 22px;
  width: 22px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: 0.3s;
}

.switch input:checked + .slider {
  background-color: #4CAF50;
}

.switch input:checked + .slider:before {
  transform: translateX(22px);
}

/* Slider/range */
.slider-container {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.slider-container input[type="range"] {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  background: #e0e0e0;
  border-radius: 3px;
}

.slider-container input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  background: #4CAF50;
  border-radius: 50%;
  cursor: pointer;
}

/* Category fieldsets */
.field-category {
  border: none;
  padding: 0;
  margin: 0;
}

.field-category legend {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a1a2e;
  padding: 0;
  margin-bottom: 1rem;
}

/* Form actions */
.form-actions {
  margin-top: 2rem;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

.btn-primary {
  background: linear-gradient(90deg, #4CAF50, #45a049);
  color: white;
  border: none;
  padding: 0.875rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.3);
}

.btn-primary:active {
  transform: translateY(0);
}

/* Conditional field visibility */
.form-field[data-show-when] {
  display: none;
}

.form-field[data-show-when].visible {
  display: block;
}
"""


# =============================================================================
# JAVASCRIPT FOR FORM INTERACTIVITY
# =============================================================================


FORM_JS = """
// Socratic Form Interactivity

class SocraticForm {
  constructor(formElement) {
    this.form = formElement;
    this.fields = {};
    this.init();
  }

  init() {
    // Index all fields
    this.form.querySelectorAll('.form-field').forEach(field => {
      const fieldId = field.dataset.fieldId;
      this.fields[fieldId] = {
        element: field,
        showWhen: field.dataset.showWhen ? JSON.parse(field.dataset.showWhen) : null,
      };
    });

    // Add change listeners
    this.form.addEventListener('change', (e) => this.handleChange(e));

    // Initial visibility check
    this.updateVisibility();

    // Slider output sync
    this.form.querySelectorAll('input[type="range"]').forEach(slider => {
      const output = slider.nextElementSibling;
      if (output && output.tagName === 'OUTPUT') {
        output.textContent = slider.value;
        slider.addEventListener('input', () => {
          output.textContent = slider.value;
        });
      }
    });
  }

  handleChange(event) {
    this.updateVisibility();
  }

  getValues() {
    const values = {};
    const formData = new FormData(this.form);

    for (const [key, value] of formData.entries()) {
      if (values[key]) {
        // Multi-select: convert to array
        if (!Array.isArray(values[key])) {
          values[key] = [values[key]];
        }
        values[key].push(value);
      } else {
        values[key] = value;
      }
    }

    return values;
  }

  updateVisibility() {
    const values = this.getValues();

    Object.entries(this.fields).forEach(([fieldId, field]) => {
      if (!field.showWhen) {
        field.element.classList.add('visible');
        return;
      }

      const shouldShow = this.evaluateCondition(field.showWhen, values);
      field.element.classList.toggle('visible', shouldShow);

      // Disable hidden inputs to exclude from submission
      const inputs = field.element.querySelectorAll('input, textarea, select');
      inputs.forEach(input => {
        input.disabled = !shouldShow;
      });
    });
  }

  evaluateCondition(condition, values) {
    for (const [fieldId, expected] of Object.entries(condition)) {
      const actual = values[fieldId];

      if (Array.isArray(expected)) {
        // Any of condition
        if (Array.isArray(actual)) {
          if (!actual.some(v => expected.includes(v))) return false;
        } else {
          if (!expected.includes(actual)) return false;
        }
      } else {
        // Exact match
        if (Array.isArray(actual)) {
          if (!actual.includes(expected)) return false;
        } else {
          if (actual !== expected) return false;
        }
      }
    }
    return true;
  }
}

// Auto-initialize forms
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.socratic-form').forEach(form => {
    new SocraticForm(form);
  });
});

// Async form submission
async function submitSocraticForm(form, url) {
  const socraticForm = form._socraticForm || new SocraticForm(form);
  const values = socraticForm.getValues();

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(values),
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Form submission failed:', error);
    throw error;
  }
}
"""


# =============================================================================
# EXPORT FUNCTIONS
# =============================================================================


def get_form_assets() -> dict[str, str]:
    """Get CSS and JS assets for forms.

    Returns:
        Dictionary with 'css' and 'js' keys
    """
    return {
        "css": FORM_CSS,
        "js": FORM_JS,
    }
