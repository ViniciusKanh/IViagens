// -*- coding: utf-8 -*-
document.addEventListener('DOMContentLoaded', () => {
  const el = (id) => document.getElementById(id);
  const $ = (sel) => document.querySelector(sel);

  // Prefs
  const themeToggle = el('themeToggle');
  const storedTheme = localStorage.getItem('ivi_theme') || 'dark';
  if (storedTheme === 'light') document.documentElement.classList.add('light');

  themeToggle.addEventListener('click', () => {
    document.documentElement.classList.toggle('light');
    localStorage.setItem('ivi_theme', document.documentElement.classList.contains('light') ? 'light' : 'dark');
  });

  const backendUrl = el('backendUrl');
  backendUrl.value = localStorage.getItem('ivi_backend') || 'http://127.0.0.1:7860';

  // Buttons
  el('btnPrint').addEventListener('click', () => window.print());
  el('copyJson').addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(el('rawJson').textContent || '');
      alert('JSON copiado.');
    } catch { alert('Falha ao copiar JSON.'); }
  });

  // Generate plan
  el('btnPlan').addEventListener('click', async () => {
    const payload = {
      destino: el('destino').value.trim(),
      data_inicio: el('dataInicio').value,
      data_fim: el('dataFim').value,
      cidade_origem: el('origem').value.trim(),
      numero_viajantes: parseInt(el('nViajantes').value || '1', 10),
      perfil: el('perfil').value,
      temas: (el('temas').value || '').split(',').map(s => s.trim()).filter(Boolean),
      moeda: el('moeda').value || 'BRL',
      teto_orcamento: parseFloat(el('teto').value || '0')
    };

    if (!payload.destino || !payload.data_inicio || !payload.data_fim || !payload.cidade_origem) {
      alert('Preencha origem, destino, data início e data fim.'); return;
    }

    localStorage.setItem('ivi_backend', backendUrl.value.trim());

    el('loading').classList.remove('hidden');
    try {
      const res = await fetch(backendUrl.value.trim() + '/plan', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const data = await res.json();
      renderPlan(data);
    } catch (e) {
      alert('Erro: ' + e.message);
    } finally {
      el('loading').classList.add('hidden');
    }
  });

  // Render
  function renderPlan(data) {
    const plan = el('plan');
    const planHtml = el('planHtml');
    const rawJson = el('rawJson');
    const kpis = el('kpis');

    // KPIs chips (quando disponíveis no contexto agregado do HTML, usamos dados básicos)
    const total = (data.orcamento_estimado_total || 0).toFixed(2);
    const dentro = !!data.dentro_do_teto;
    const sobra = (data.sobra_ou_deficit || 0).toFixed(2);
    kpis.innerHTML = `
      <span class="chip ${dentro ? 'ok':'bad'}">Teto: ${dentro ? 'dentro' : 'excede'}</span>
      <span class="chip">${data.moedas || 'BRL'} ${total}</span>
      <span class="chip ${parseFloat(sobra) >= 0 ? 'ok':'warn'}">Sobra/deficit: ${data.moedas || 'BRL'} ${sobra}</span>
      <span class="chip">Dias: ${(data.roteiro||[]).length}</span>
    `;

    // Documento final
    planHtml.innerHTML = data.plano_html || "<p>Plano não recebido.</p>";
    rawJson.textContent = JSON.stringify(data, null, 2);

    // TOC dinâmico
    buildTOC();

    // Export .ics
    el('btnExportIcs').onclick = () => exportICS(data);

    plan.classList.remove('hidden');
    plan.scrollIntoView({ behavior: 'smooth' });
  }

  function buildTOC() {
    const toc = el('toc');
    const headings = [...document.querySelectorAll('#planHtml h2, #planHtml h3')];
    headings.forEach((h, i) => {
      if (!h.id) h.id = 'sec-' + i;
    });
    toc.innerHTML = headings.map(h => {
      const level = h.tagName === 'H2' ? '' : '&nbsp;&nbsp;• ';
      return `<a href="#${h.id}">${level}${h.textContent}</a>`;
    }).join('');
  }

  // Exportar .ics a partir do roteiro
  function exportICS(data) {
    const days = data.roteiro || [];
    if (!days.length) { alert('Sem roteiro para exportar.'); return; }

    const lines = [
      'BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//IViagem//PT-BR//'
    ];
    // mapas: manhã/tarde/noite para slots
    const startDate = new Date(data.data_inicio + 'T00:00:00');
    const tz = 'UTC'; // simples; se quiser, localize por fuso

    const slotTimes = { // HHMMSS
      'manha': ['083000','120000'],
      'tarde': ['133000','173000'],
      'noite': ['190000','220000']
    };

    days.forEach((dia, idx) => {
      const base = new Date(startDate.getTime());
      base.setDate(base.getDate() + idx);
      const y = base.getUTCFullYear();
      const m = String(base.getUTCMonth()+1).padStart(2,'0');
      const d = String(base.getUTCDate()).padStart(2,'0');

      ['manha','tarde','noite'].forEach(slot => {
        const acts = dia[slot] || [];
        if (!acts.length) return;
        const [sh, eh] = slotTimes[slot];
        const dtStart = `${y}${m}${d}T${sh}Z`;
        const dtEnd   = `${y}${m}${d}T${eh}Z`;
        const title = acts.map(a => a.nome).join(' · ');
        const desc  = acts.map(a => `- ${a.nome} (${a.categoria_custo || ''}) ${a.observacoes? ' — '+a.observacoes:''}`).join('\\n');

        lines.push(
          'BEGIN:VEVENT',
          `UID:${cryptoRandom()}@iviagem`,
          `DTSTAMP:${y}${m}${d}T000000Z`,
          `DTSTART:${dtStart}`,
          `DTEND:${dtEnd}`,
          `SUMMARY:${escapeICS(title)}`,
          `DESCRIPTION:${escapeICS(desc)}`,
          'END:VEVENT'
        );
      });
    });

    lines.push('END:VCALENDAR');
    const blob = new Blob([lines.join('\r\n')], {type: 'text/calendar'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'iviagem-roteiro.ics';
    a.click();
    URL.revokeObjectURL(url);
  }

  function escapeICS(s=''){ return s.replace(/([,;])/g,'\\$1').replace(/\n/g,'\\n'); }
  function cryptoRandom(){
    if (window.crypto?.getRandomValues) {
      const arr = new Uint32Array(2); window.crypto.getRandomValues(arr);
      return (arr[0].toString(16)+arr[1].toString(16)).padStart(16,'0');
    }
    return Math.random().toString(16).slice(2);
  }
});
