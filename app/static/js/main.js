// Hero video crossfade
(function(){
  const videos = document.querySelectorAll('.hero-video');
  if (videos.length < 2) return;
  let i = 0;
  videos.forEach((v, idx) => { if (idx !== 0) v.style.opacity = '0'; });
  function showNext() {
    const cur = videos[i];
    i = (i + 1) % videos.length;
    const next = videos[i];
    next.style.opacity = '1';
    cur.style.opacity = '0';
    try { next.play(); } catch(e){}
  }
  setInterval(showNext, 6000);
  videos.forEach(v => { try { v.play(); } catch(e){} });
})();

// Reveal on scroll
(function(){
  const els = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window)) { els.forEach(e=>e.classList.add('visible')); return; }
  const io = new IntersectionObserver(entries => {
    entries.forEach(en => { if (en.isIntersecting) { en.target.classList.add('visible'); io.unobserve(en.target); } });
  }, { threshold: 0.12 });
  els.forEach((e, idx) => { e.style.transitionDelay = (idx % 6) * 0.08 + 's'; io.observe(e); });
})();

// Image gallery
(function(){
  document.querySelectorAll('.gallery').forEach(g => {
    const main = g.querySelector('.gallery-main');
    g.querySelectorAll('.gallery-thumb').forEach(t => {
      t.addEventListener('click', () => {
        if (main) main.src = t.dataset.src;
        g.querySelectorAll('.gallery-thumb').forEach(x => x.classList.remove('active'));
        t.classList.add('active');
      });
    });
  });
})();

const CSRF = (document.querySelector('meta[name="csrf-token"]')||{}).content || '';

// Visitor identification
function identifyVisitor(callback) {
  if (window.VISITOR_PROMPTED) { callback(); return; }
  const modalEl = document.getElementById('visitorModal');
  if (!modalEl || !window.bootstrap) { window.VISITOR_PROMPTED = true; callback(); return; }
  const modal = new bootstrap.Modal(modalEl);
  modal.show();
  let finished = false;
  modalEl.addEventListener('hidden.bs.modal', () => {
    if (!finished) { finished = true; callback(); }
  }, {once: true});
  function finish(name, email) {
    if (finished) return;
    fetch('/visitor/identify', {method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF}, body: JSON.stringify({name:name, email:email})})
      .then(async res => {
        if (!res.ok) throw new Error('Please enter a valid name and email, or continue without email.');
        finished = true; window.VISITOR_PROMPTED = true; modal.hide(); callback();
      }).catch(err => alert(err.message));
  }
  document.getElementById('visitorContinue').onclick = () => {
    finish(document.getElementById('visitorName').value, document.getElementById('visitorEmail').value);
  };
  document.getElementById('visitorSkip').onclick = () => {
    finish(null, null);
  };
}

// Like button
document.querySelectorAll('.like-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    identifyVisitor(async () => {
      const id = btn.dataset.id;
      try {
        const res = await fetch(`/like/${id}`, {method:'POST', headers:{'X-CSRFToken':CSRF}});
        const data = await res.json();
        const c = btn.querySelector('.like-count');
        if (c) c.textContent = data.likes;
        btn.classList.add('liked');
      } catch(e){}
    });
  });
});

// Yes interest
document.querySelectorAll('.yes-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    identifyVisitor(async () => {
      const id = btn.dataset.id;
      const res = await fetch(`/interest/${id}`, {method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF}, body: JSON.stringify({answer:'yes'})});
      const data = await res.json();
      if (data.redirect) window.location.href = data.redirect;
    });
  });
});

// No interest
document.querySelectorAll('.no-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    identifyVisitor(async () => {
      const id = btn.dataset.id;
      await fetch(`/interest/${id}`, {method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF}, body: JSON.stringify({answer:'no'})});
    });
  });
});

// Track WhatsApp/phone clicks
document.querySelectorAll('.wa-link').forEach(link => {
  link.addEventListener('click', () => {
    const id = link.dataset.id;
    if (id) fetch(`/track/${id}/WHATSAPP_CLICK`, {method:'POST', keepalive:true, headers:{'X-CSRFToken':CSRF}}).catch(() => {});
  });
});
document.querySelectorAll('.phone-link').forEach(link => {
  link.addEventListener('click', () => {
    const id = link.dataset.id;
    if (id) fetch(`/track/${id}/PHONE_CLICK`, {method:'POST', keepalive:true, headers:{'X-CSRFToken':CSRF}}).catch(() => {});
  });
});

function subscribeNewsletter(e) {
  e.preventDefault();
  const email = document.getElementById('newsletterEmail').value;
  fetch('/newsletter/subscribe', {method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF}, body: JSON.stringify({email: email})})
    .then(r => r.json())
    .then(data => {
      if (data.ok) {
        alert('Subscribed. Thank you!');
        document.getElementById('newsletterEmail').value = '';
      } else {
        alert('Please enter a valid email.');
      }
    }).catch(() => alert('Please enter a valid email.'));
}
