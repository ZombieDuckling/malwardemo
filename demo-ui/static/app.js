(function () {
  'use strict';

  var serverOk = false;
  var containerRunning = false;
  var sessionActive = false;
  var containerStarting = false;

  var containerActivityOutput = document.getElementById('containerActivityOutput');
  var victimIframe = document.getElementById('victimIframe');
  var liveViewState = document.getElementById('liveViewState');

  var serverOffline = document.getElementById('serverOffline');
  var connectionPill = document.getElementById('connectionPill');
  var connectionText = document.getElementById('connectionText');
  var btnStartContainers = document.getElementById('btnStartContainers');
  var step1Feedback = document.getElementById('step1Feedback');
  var step1State = document.getElementById('step1State');
  var step2State = document.getElementById('step2State');
  var step3State = document.getElementById('step3State');
  var step2Feedback = document.getElementById('step2Feedback');
  var emailRow = document.getElementById('emailRow');
  var emailList = document.getElementById('emailList');
  var emailOpen = document.getElementById('emailOpen');
  var btnOpenAttachment = document.getElementById('btnOpenAttachment');
  var victimGuiLink = document.getElementById('victimGuiLink');
  var listenerStatus = document.getElementById('listenerStatus');
  var listenerText = document.getElementById('listenerText');
  var sessionBanner = document.getElementById('sessionBanner');
  var terminalOutput = document.getElementById('terminalOutput');
  var inputWrap = document.getElementById('inputWrap');
  var terminalInput = document.getElementById('terminalInput');

  var step1Card = document.getElementById('step1');
  var step2Card = document.getElementById('step2');
  var step3Card = document.getElementById('step3');

  var pipe1 = document.getElementById('pipe1');
  var pipe2 = document.getElementById('pipe2');
  var pipe3 = document.getElementById('pipe3');
  var pipe4 = document.getElementById('pipe4');

  var attackLogEntries = document.getElementById('attackLogEntries');
  var attackLogPlaceholder = document.getElementById('attackLogPlaceholder');
  var lastAttackLogCount = 0;

  function setOffline(offline) {
    if (!serverOffline) return;
    serverOffline.hidden = !offline;
    if (connectionPill) {
      connectionPill.classList.toggle('connected', !offline && serverOk);
      if (connectionText) {
        connectionText.textContent = offline ? 'Server not running' : (serverOk ? 'Connected' : 'Checking…');
      }
    }
  }

  function setStepCards() {
    if (step1Card) {
      step1Card.classList.toggle('active', serverOk && !containerRunning && !sessionActive);
      step1Card.classList.toggle('done', containerRunning || sessionActive);
    }
    if (step2Card) {
      step2Card.classList.toggle('active', containerRunning && !sessionActive);
      step2Card.classList.toggle('done', sessionActive);
    }
    if (step3Card) {
      step3Card.classList.toggle('active', sessionActive);
    }
    if (step1State) step1State.textContent = containerRunning ? 'Running' : (serverOk ? 'Ready' : 'Pending');
    if (step2State) step2State.textContent = sessionActive ? 'Connected' : (containerRunning ? 'Ready' : 'Waiting');
    if (step3State) step3State.textContent = sessionActive ? 'Active' : 'Waiting for beacon';

    // Process pipeline: 1 Deploy → 2 Execute → 3 Beacon → 4 C2
    if (pipe1) {
      pipe1.classList.toggle('active', serverOk && !containerRunning);
      pipe1.classList.toggle('done', containerRunning);
    }
    if (pipe2) {
      pipe2.classList.toggle('active', containerRunning && !sessionActive);
      pipe2.classList.toggle('done', sessionActive);
    }
    if (pipe3) {
      pipe3.classList.toggle('active', containerRunning && !sessionActive);
      pipe3.classList.toggle('done', sessionActive);
    }
    if (pipe4) {
      pipe4.classList.toggle('active', sessionActive);
      pipe4.classList.toggle('done', sessionActive);
    }
  }

  function setContainerUI(running, starting) {
    containerRunning = !!running;
    if (step1Feedback) {
      if (starting) {
        step1Feedback.textContent = 'Starting container…';
        step1Feedback.className = 'step-feedback';
      } else if (running) {
        step1Feedback.textContent = 'Container is running.';
        step1Feedback.className = 'step-feedback success';
      } else {
        step1Feedback.textContent = '';
      }
    }
    if (btnStartContainers) {
      btnStartContainers.disabled = running || starting;
    }
    if (btnOpenAttachment) btnOpenAttachment.disabled = !running;
    if (victimGuiLink) victimGuiLink.hidden = !running;
    setStepCards();
  }

  function log(msg, className) {
    if (!terminalOutput) return;
    var line = document.createElement('div');
    line.className = className || 'line-out';
    line.textContent = msg;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  function pollStatus() {
    fetch('/api/status')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        serverOk = true;
        setOffline(false);
        if (connectionText) connectionText.textContent = 'Connected';

        if (!containerStarting || data.container_running) {
          if (data.container_running) containerStarting = false;
          setContainerUI(!!data.container_running, false);
          if (data.container_running) pollContainerActivity();
        }

        if (listenerText) {
          if (data.listening) {
            if (listenerStatus) listenerStatus.classList.add('active');
            listenerText.textContent = 'Listening on 0.0.0.0:' + data.port;
          } else {
            listenerText.textContent = 'Starting…';
          }
        }

        sessionActive = !!data.session_active;
        if (data.session_active) {
          if (listenerStatus) {
            listenerStatus.classList.remove('active');
            listenerStatus.classList.add('session');
          }
          if (listenerText) listenerText.textContent = 'Session active — implant connected';
          if (sessionBanner) {
            sessionBanner.textContent = (data.banner || '').trim();
            sessionBanner.hidden = !data.banner;
          }
          if (inputWrap) inputWrap.hidden = false;
          if (terminalInput) terminalInput.focus();
          if (step2Feedback) {
            step2Feedback.textContent = 'Connection established. You have control.';
            step2Feedback.className = 'step-feedback inline success';
          }
        } else {
          if (sessionBanner) sessionBanner.hidden = true;
          if (inputWrap) inputWrap.hidden = true;
          if (step2Feedback && !step2Feedback.classList.contains('success') && step2Feedback.textContent.indexOf('Opening') === -1) {
            if (data.container_running) {
              step2Feedback.textContent = 'Click the email above, then "Open attachment".';
              step2Feedback.className = 'step-feedback inline';
            } else {
              step2Feedback.textContent = 'Deploy the target (step 1) first.';
              step2Feedback.className = 'step-feedback inline';
            }
          }
        }
        setStepCards();
      })
      .catch(function () {
        serverOk = false;
        setOffline(true);
        if (connectionText) connectionText.textContent = 'Server not running';
        if (listenerText) listenerText.textContent = '—';
        setStepCards();
      });
  }

  function pollContainerActivity() {
    if (!containerRunning || !containerActivityOutput) return;
    fetch('/api/container-activity')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (containerActivityOutput && data.output !== undefined) {
          containerActivityOutput.textContent = data.output;
        }
      })
      .catch(function () {});
  }

  function pollAttackLog() {
    fetch('/api/attack-log')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data.events || !Array.isArray(data.events) || data.events.length === lastAttackLogCount) return;
        lastAttackLogCount = data.events.length;
        if (!attackLogEntries || !attackLogPlaceholder) return;
        attackLogPlaceholder.hidden = data.events.length > 0;
        attackLogEntries.innerHTML = '';
        data.events.forEach(function (ev) {
          var row = document.createElement('div');
          row.className = 'attack-log-entry';
          var time = (ev.ts || '').replace('T', ' ').replace(/\..*$/, '') || '—';
          var tag = ev.event || 'event';
          var tagClass = tag.replace('_', '-');
          var detail = ev.detail || '';
          row.innerHTML =
            '<span class="attack-log-time">' + escapeHtml(time) + '</span>' +
            '<span class="attack-log-tag ' + escapeHtml(tagClass) + '">' + escapeHtml(tag) + '</span>' +
            '<span class="attack-log-detail">' + escapeHtml(detail) + '</span>';
          attackLogEntries.appendChild(row);
        });
        if (attackLogEntries.parentElement) {
          attackLogEntries.parentElement.scrollTop = attackLogEntries.parentElement.scrollHeight;
        }
      })
      .catch(function () {});
  }

  function escapeHtml(s) {
    if (s == null) return '';
    var div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
  }

  pollStatus();
  setInterval(pollStatus, 1500);
  setInterval(pollAttackLog, 1000);

  setInterval(function () {
    if (containerRunning) {
      pollContainerActivity();
      if (victimIframe && victimIframe.src === 'about:blank') {
        var host = window.location.hostname || '127.0.0.1';
        victimIframe.src = 'http://' + host + ':8080';
      }
    }
  }, 2000);

  if (btnStartContainers) {
    btnStartContainers.addEventListener('click', function () {
      btnStartContainers.disabled = true;
      containerStarting = true;
      setContainerUI(false, true);
      if (step1Feedback) {
        step1Feedback.textContent = 'Starting…';
        step1Feedback.className = 'step-feedback';
      }
      fetch('/api/start-containers', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.ok) {
            pollStatus();
            [2000, 5000, 8000].forEach(function (ms) { setTimeout(pollStatus, ms); });
          } else {
            containerStarting = false;
            if (step1Feedback) {
              step1Feedback.textContent = 'Error: ' + (data.message || 'Failed');
              step1Feedback.className = 'step-feedback error';
            }
            btnStartContainers.disabled = false;
            setContainerUI(false, false);
          }
        })
        .catch(function () {
          containerStarting = false;
          if (step1Feedback) {
            step1Feedback.textContent = 'Request failed. Is the server running?';
            step1Feedback.className = 'step-feedback error';
          }
          btnStartContainers.disabled = false;
          setContainerUI(false, false);
        });
    });
  }

  if (emailRow && emailList && emailOpen) {
    emailRow.addEventListener('click', function () {
      emailList.hidden = true;
      emailOpen.hidden = false;
    });
  }

  if (btnOpenAttachment) {
    btnOpenAttachment.addEventListener('click', function () {
      btnOpenAttachment.disabled = true;
      if (step2Feedback) {
        step2Feedback.textContent = 'Opening attachment…';
        step2Feedback.className = 'step-feedback inline';
      }
      fetch('/api/trigger-victim', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (step2Feedback) {
            step2Feedback.textContent = data.ok ? 'Payload triggered. Waiting for connection…' : ('Error: ' + (data.message || ''));
            step2Feedback.className = 'step-feedback inline ' + (data.ok ? '' : 'error');
          }
          if (!data.ok) btnOpenAttachment.disabled = false;
        })
        .catch(function () {
          if (step2Feedback) {
            step2Feedback.textContent = 'Request failed.';
            step2Feedback.className = 'step-feedback inline error';
          }
          btnOpenAttachment.disabled = false;
        });
    });
  }

  function runCommand(cmd) {
    cmd = (cmd || '').trim();
    if (!cmd) return;
    if (terminalInput) terminalInput.value = '';
    log('c2> ' + cmd, 'line-cmd');
    fetch('/api/command', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cmd: cmd }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.ok) {
          log(data.output, 'line-out');
        } else {
          log('Error: ' + (data.output || data.message || 'Unknown'), 'line-out');
        }
      })
      .catch(function () {
        log('Request failed.', 'line-out');
      });
  }

  if (terminalInput) {
    terminalInput.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter') return;
      runCommand(terminalInput.value.trim());
      terminalInput.value = '';
    });
  }

})();
