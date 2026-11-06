// Video generation UI for product pages
(function() {
  const pollInterval = 3000; // Check status every 3s
  const maxPolls = 120; // Give up after 6 minutes

  function generateVideo(asin, description) {
    const btn = document.querySelector(`[data-generate-video="${asin}"]`);
    if (!btn) return;

    btn.disabled = true;
    btn.textContent = '⏳ Generating script...';

    fetch('/api/generate-video.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ asin, description })
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          btn.textContent = '❌ Generation failed';
          btn.disabled = false;
          return;
        }
        if (data.status === 'exists') {
          displayVideo(asin, data.video, btn);
          return;
        }
        // Poll for completion
        pollVideoStatus(asin, data.job_id, btn, 0);
      })
      .catch(err => {
        console.error('Video generation error:', err);
        btn.textContent = '❌ Error';
        btn.disabled = false;
      });
  }

  function pollVideoStatus(asin, jobId, btn, pollCount) {
    if (pollCount > maxPolls) {
      btn.textContent = '⏱️ Taking too long';
      btn.disabled = false;
      return;
    }

    setTimeout(() => {
      fetch('/api/video-status.php', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, asin })
      })
        .then(r => r.json())
        .then(data => {
          if (data.status === 'completed') {
            displayVideo(asin, data.video, btn);
          } else if (data.status === 'failed') {
            btn.textContent = '❌ Generation failed';
            btn.disabled = false;
          } else {
            btn.textContent = `⏳ Rendering... (${Math.floor(pollCount / 10)}%)`;
            pollVideoStatus(asin, jobId, btn, pollCount + 1);
          }
        })
        .catch(() => {
          // Retry on network error
          pollVideoStatus(asin, jobId, btn, pollCount + 1);
        });
    }, pollInterval);
  }

  function displayVideo(asin, videoUrl, btn) {
    const container = btn.closest('.product-video-container') || btn.parentElement;

    // Remove button
    btn.remove();

    // Add video player
    const video = document.createElement('video');
    video.src = videoUrl;
    video.controls = true;
    video.style.maxWidth = '100%';
    video.style.marginTop = '12px';
    video.style.borderRadius = '8px';
    container.appendChild(video);

    // Auto-play on mobile, not on desktop
    if (window.innerWidth < 768) {
      video.autoplay = true;
      video.muted = true;
    }
  }

  // Hook up all video generation buttons
  document.addEventListener('click', function(e) {
    if (e.target.matches('[data-generate-video]')) {
      const asin = e.target.getAttribute('data-generate-video');
      const desc = e.target.getAttribute('data-description') || 'Product demo';
      generateVideo(asin, desc);
      e.preventDefault();
    }
  });

  // Check for existing videos on page load
  document.querySelectorAll('[data-video-check]').forEach(el => {
    const asin = el.getAttribute('data-video-check');
    const videoEl = el.querySelector(`[data-video="${asin}"]`);
    if (videoEl && videoEl.src) {
      // Video exists, show it
      el.querySelector('[data-generate-video]')?.remove();
    }
  });
})();
