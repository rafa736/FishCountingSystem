/**
 * FishCountAI v2.0 — script.js  (Portfolio Edition)
 * =====================================================
 * Changelog v2:
 *  - Confidence threshold slider (dinamis ke backend)
 *  - Result rendering: density heatmap, conf histogram
 *  - Detection table dengan confidence bar per baris
 *  - Session history: render riwayat dari /history
 *  - Session stats bar: update dari /stats
 *  - Animasi masuk smooth di setiap section
 */

"use strict";

/* ── Particle System ──────────────────────────────────────────────────────── */
(function initParticles() {
  const canvas = document.getElementById('particle-canvas');
  if (!canvas) return;

  const ctx = canvas.getContext('2d');
  let particles = [];
  let W, H;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  class Particle {
    constructor() { this.reset(); }
    reset() {
      this.x  = Math.random() * W;
      this.y  = Math.random() * H;
      this.r  = Math.random() * 1.5 + 0.3;
      this.vx = (Math.random() - 0.5) * 0.28;
      this.vy = (Math.random() - 0.5) * 0.28;
      this.a  = Math.random() * 0.45 + 0.1;
    }
    update() {
      this.x += this.vx;
      this.y += this.vy;
      if (this.x < 0 || this.x > W || this.y < 0 || this.y > H) this.reset();
    }
    draw() {
      ctx.beginPath();
      ctx.arc(this.x, this.y, this.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(0, 200, 255, ${this.a})`;
      ctx.fill();
    }
  }

  function createParticles(n = 90) {
    particles = Array.from({ length: n }, () => new Particle());
  }

  function drawLines() {
    const maxDist = 100;
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const d  = Math.sqrt(dx * dx + dy * dy);
        if (d < maxDist) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(0, 200, 255, ${(1 - d / maxDist) * 0.1})`;
          ctx.lineWidth   = 0.5;
          ctx.stroke();
        }
      }
    }
  }

  function loop() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => { p.update(); p.draw(); });
    drawLines();
    requestAnimationFrame(loop);
  }

  window.addEventListener('resize', () => { resize(); createParticles(); });
  resize();
  createParticles();
  loop();
})();


/* ── Confidence Slider ────────────────────────────────────────────────────── */
const confSlider  = document.getElementById('conf-slider');
const confDisplay = document.getElementById('conf-display');

function updateSliderStyle() {
  if (!confSlider) return;
  const pct = ((confSlider.value - confSlider.min) / (confSlider.max - confSlider.min)) * 100;
  confSlider.style.setProperty('--slider-pct', pct + '%');
  confDisplay.textContent = (confSlider.value / 100).toFixed(2);
}

if (confSlider) {
  confSlider.addEventListener('input', updateSliderStyle);
  updateSliderStyle();
}

function getConfThreshold() {
  return confSlider ? confSlider.value / 100 : 0.25;
}


/* ── Upload & Drag-and-Drop ───────────────────────────────────────────────── */
let selectedFile = null;

const dropZone    = document.getElementById('drop-zone');
const fileInput   = document.getElementById('file-input');
const dropIdle    = document.getElementById('drop-idle');
const dropPreview = document.getElementById('drop-preview');
const previewImg  = document.getElementById('preview-img');
const fileNameEl  = document.getElementById('file-name');
const btnDetect   = document.getElementById('btn-detect');

function setFile(file) {
  if (!file || !file.type.startsWith('image/')) return;
  selectedFile = file;
  fileNameEl.textContent = file.name + ' (' + formatBytes(file.size) + ')';
  btnDetect.disabled = false;

  const reader = new FileReader();
  reader.onload = e => {
    previewImg.src = e.target.result;
    dropIdle.classList.add('hidden');
    dropPreview.classList.remove('hidden');
  };
  reader.readAsDataURL(file);
}

function formatBytes(bytes) {
  if (bytes < 1024)   return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(2) + ' MB';
}

if (dropZone) {
  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
  });
  dropZone.addEventListener('click', e => {
    if (e.target === dropZone || e.target.closest('.drop-idle')) {
      fileInput.click();
    }
  });
}

if (fileInput) {
  fileInput.addEventListener('change', () => {
    if (fileInput.files[0]) setFile(fileInput.files[0]);
  });
}


/* ── Detection ───────────────────────────────────────────────────────────── */
const loadingOverlay = document.getElementById('loading-overlay');
const resultSection  = document.getElementById('result-section');

window.startDetection = async function () {
  if (!selectedFile) return;

  loadingOverlay.classList.remove('hidden');
  resultSection.classList.add('hidden');

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('conf_threshold', getConfThreshold());

  try {
    const resp = await fetch('/detect', { method: 'POST', body: formData });
    const json = await resp.json();

    loadingOverlay.classList.add('hidden');

    if (json.success) {
      renderResult(json.data);
      updateSessionStats();
      appendHistory(json.data);
    } else {
      showError(json.error || 'Deteksi gagal.');
    }
  } catch (err) {
    loadingOverlay.classList.add('hidden');
    showError('Tidak dapat terhubung ke server: ' + err.message);
  }
};


/* ── Render Result ───────────────────────────────────────────────────────── */
function renderResult(data) {
  const {
    fish_count, detections, statistics, density_map, conf_histogram,
    upload_image, result_image, file_size,
    processing_time_ms, image_info, analysis_text, confidence_level,
    conf_threshold_used, timestamp, demo_mode
  } = data;

  const stats   = statistics || {};
  const imgW    = image_info ? image_info.width  : '?';
  const imgH    = image_info ? image_info.height : '?';
  const timeStr = new Date(timestamp).toLocaleTimeString('id-ID');

  resultSection.innerHTML = `
    <div class="result-header">
      <div>
        <h2 class="result-title">Hasil Deteksi${demo_mode ? ' <span style="font-size:.8rem;color:var(--yellow)">(Demo Mode)</span>' : ''}</h2>
        <div class="result-meta">
          ${timeStr} &nbsp;·&nbsp; ${imgW}×${imgH}px &nbsp;·&nbsp; ${file_size} &nbsp;·&nbsp; ${processing_time_ms} ms &nbsp;·&nbsp; conf ≥ ${(conf_threshold_used * 100).toFixed(0)}%
        </div>
      </div>
      <div class="result-actions">
        <a href="/download/${result_image}" class="btn-action btn-download" download>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          Unduh Hasil
        </a>
        <button class="btn-action btn-reset" onclick="resetDetection()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-4.16"/>
          </svg>
          Deteksi Ulang
        </button>
      </div>
    </div>

    <!-- Stat cards -->
    <div class="stat-cards" style="margin-bottom:var(--gap)">
      ${statCard('🐟', fish_count, 'Ikan Terdeteksi')}
      ${statCard('🎯', stats.avg_confidence ? stats.avg_confidence.toFixed(1) + '%' : '—', 'Conf. Rata-rata')}
      ${statCard('⬆️', stats.max_confidence ? stats.max_confidence.toFixed(1) + '%' : '—', 'Conf. Tertinggi')}
      ${statCard('⚡', processing_time_ms + ' ms', 'Waktu Proses')}
    </div>

    <!-- Image compare -->
    <div class="img-compare" style="margin-bottom:var(--gap)">
      <div class="img-panel">
        <div class="img-panel-label">Gambar Original</div>
        <img src="/static/uploads/${upload_image}" alt="Original" loading="lazy" />
      </div>
      <div class="img-panel">
        <div class="img-panel-label">Hasil Deteksi YOLOv8</div>
        <img src="/static/results/${result_image}" alt="Hasil" loading="lazy" />
      </div>
    </div>

    <!-- Analysis + Density side by side -->
    <div class="result-grid" style="margin-bottom:var(--gap)">
      <div class="analysis-card">
        <div class="analysis-title">Analisis Otomatis</div>
        <p class="analysis-text">${analysis_text}</p>
        ${confidence_level ? `<span class="confidence-badge badge-${confidence_level.badge}">
          ● ${confidence_level.level}
        </span>` : ''}
      </div>
      <div class="density-card">
        <div class="density-title">Density Map (4×4 Grid)</div>
        ${renderDensityMap(density_map, fish_count)}
      </div>
    </div>

    <!-- Histogram + Table -->
    <div class="result-grid" style="margin-bottom:var(--gap)">
      <div class="histogram-card">
        <div class="histogram-title">Distribusi Confidence</div>
        ${renderHistogram(conf_histogram)}
      </div>
      <div></div>
    </div>

    ${renderDetectionTable(detections)}
  `;

  resultSection.classList.remove('hidden');
  resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function statCard(icon, value, label) {
  return `<div class="stat-card">
    <div class="stat-card-icon">${icon}</div>
    <span class="stat-card-val">${value}</span>
    <span class="stat-card-label">${label}</span>
  </div>`;
}

/* ── Density Map ─────────────────────────────────────────────────────────── */
function renderDensityMap(densityMap, totalFish) {
  if (!densityMap || densityMap.length === 0) {
    return '<p style="color:var(--text-muted);font-size:.85rem">Data tidak tersedia</p>';
  }

  const maxCount = Math.max(...densityMap.map(c => c.count), 1);

  const cells = densityMap.map(cell => {
    const intensity = cell.count / maxCount;
    const bg = cell.count === 0
      ? 'rgba(0,200,255,0.06)'
      : `rgba(0,200,255,${0.2 + intensity * 0.7})`;
    return `<div class="density-cell" style="background:${bg}" title="Baris ${cell.row+1}, Kolom ${cell.col+1}: ${cell.count} ikan">
      ${cell.count > 0 ? cell.count : ''}
    </div>`;
  }).join('');

  return `<div class="density-grid">${cells}</div>
    <p style="font-size:.72rem;color:var(--text-muted);margin-top:.6rem;font-family:var(--font-mono)">
      Sebaran ${totalFish} ikan pada gambar (warna makin terang = makin padat)
    </p>`;
}

/* ── Histogram ───────────────────────────────────────────────────────────── */
function renderHistogram(histogram) {
  if (!histogram || histogram.length === 0) {
    return '<p style="color:var(--text-muted);font-size:.85rem">Data tidak tersedia</p>';
  }

  const maxCount = Math.max(...histogram.map(b => b.count), 1);

  const bars = histogram.map(bucket => {
    const heightPct = Math.max((bucket.count / maxCount) * 100, bucket.count > 0 ? 4 : 0);
    return `<div class="hbar-wrap">
      <div class="hbar" style="height:${heightPct}%"></div>
      <div class="hbar-lbl">${bucket.label}</div>
    </div>`;
  }).join('');

  return `<div class="histogram-bars">${bars}</div>`;
}

/* ── Detection Table ─────────────────────────────────────────────────────── */
function renderDetectionTable(detections) {
  if (!detections || detections.length === 0) {
    return '';
  }

  const rows = detections.map(det => {
    const pct       = det.confidence.toFixed(1);
    const tagClass  = confTagClass(det.confidence);
    const [x1,y1,x2,y2] = det.bbox;
    const bboxStr   = `(${Math.round(x1)},${Math.round(y1)}) → (${Math.round(x2)},${Math.round(y2)})`;

    return `<tr>
      <td><span style="font-family:var(--font-mono);font-weight:700;color:var(--accent)">#${det.id}</span></td>
      <td>${det.class_name}</td>
      <td>
        <div class="conf-bar-inline">
          <div class="conf-bar-track">
            <div class="conf-bar-fill" style="width:${pct}%"></div>
          </div>
          <span style="font-family:var(--font-mono);font-size:.82rem">${pct}%</span>
          <span class="conf-lbl-tag ${tagClass}">${det.confidence_label || ''}</span>
        </div>
      </td>
      <td style="font-family:var(--font-mono);font-size:.78rem;color:var(--text-muted)">${bboxStr}</td>
    </tr>`;
  }).join('');

  return `<div class="det-table-card">
    <div class="det-table-header">
      <span class="det-table-title">Daftar Deteksi (${detections.length} objek)</span>
    </div>
    <div style="overflow-x:auto">
      <table class="det-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Kelas</th>
            <th>Confidence</th>
            <th>Bounding Box</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  </div>`;
}

function confTagClass(conf) {
  if (conf >= 85) return 'tag-very-high';
  if (conf >= 70) return 'tag-high';
  if (conf >= 50) return 'tag-mid';
  return 'tag-low';
}


/* ── Session Stats ───────────────────────────────────────────────────────── */
async function updateSessionStats() {
  try {
    const resp = await fetch('/stats');
    const json = await resp.json();
    if (!json.success) return;

    const d = json.data;
    animCount('sb-total-images', d.total_images);
    animCount('sb-total-fish',   d.total_fish);

    const avgConfEl = document.getElementById('sb-avg-conf');
    const avgTimeEl = document.getElementById('sb-avg-time');
    if (avgConfEl) avgConfEl.textContent = d.avg_confidence ? d.avg_confidence.toFixed(1) + '%' : '—';
    if (avgTimeEl) avgTimeEl.textContent = d.avg_time_ms ? d.avg_time_ms.toFixed(0) + ' ms' : '—';
  } catch (_) {}
}

function animCount(id, target) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = parseInt(el.textContent) || 0;
  const duration = 600;
  const startTime = performance.now();

  function step(now) {
    const progress = Math.min((now - startTime) / duration, 1);
    el.textContent = Math.round(start + (target - start) * progress);
    if (progress < 1) requestAnimationFrame(step);
  }

  requestAnimationFrame(step);
}

// Load stats on page load
updateSessionStats();


/* ── History ─────────────────────────────────────────────────────────────── */
function appendHistory(data) {
  const list = document.getElementById('history-list');
  if (!list) return;

  // Remove empty placeholder
  const empty = list.querySelector('.history-empty');
  if (empty) empty.remove();

  const timeStr  = new Date(data.timestamp).toLocaleTimeString('id-ID');
  const avgConf  = data.statistics && data.statistics.avg_confidence
    ? data.statistics.avg_confidence.toFixed(1) + '%' : '—';

  const item = document.createElement('div');
  item.className = 'history-item';
  item.innerHTML = `
    <img class="history-thumb"
         src="/static/results/${data.result_image}"
         alt="thumb"
         onerror="this.src='/static/uploads/${data.upload_image}'" />
    <div class="history-info">
      <div class="history-count">${data.fish_count} ekor ikan</div>
      <div class="history-meta">Conf rata-rata: ${avgConf} &nbsp;·&nbsp; ${data.file_size} &nbsp;·&nbsp; ${data.processing_time_ms} ms</div>
    </div>
    <div class="history-time">${timeStr}</div>
  `;

  list.insertBefore(item, list.firstChild);
}


/* ── Reset ───────────────────────────────────────────────────────────────── */
window.resetDetection = function () {
  selectedFile = null;
  if (fileInput)   fileInput.value = '';
  if (fileNameEl)  fileNameEl.textContent = 'Belum ada file dipilih';
  if (btnDetect)   btnDetect.disabled = true;
  if (dropPreview) dropPreview.classList.add('hidden');
  if (dropIdle)    dropIdle.classList.remove('hidden');
  if (previewImg)  previewImg.src = '';
  if (resultSection) resultSection.classList.add('hidden');

  document.getElementById('upload-section')
    ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
};


/* ── Error ───────────────────────────────────────────────────────────────── */
function showError(msg) {
  resultSection.innerHTML = `
    <div style="background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);
                border-radius:var(--radius);padding:1.5rem;color:var(--red);font-family:var(--font-mono)">
      <strong>Error:</strong> ${msg}
    </div>`;
  resultSection.classList.remove('hidden');
  resultSection.scrollIntoView({ behavior: 'smooth' });
}
