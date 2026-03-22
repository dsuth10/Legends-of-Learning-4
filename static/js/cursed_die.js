/**
 * Projector page: poll display-result API and animate die.
 */
(function () {
  const classId = window.CURSED_DIE_EVENT_ID != null ? window.CURSED_DIE_CLASS_ID : null;
  const eventId = window.CURSED_DIE_EVENT_ID;

  const cube = document.getElementById('dieCube');
  const faceNum = document.getElementById('dieFaceNum');
  const resultText = document.getElementById('dieResultText');

  if (!cube || !eventId || !classId) {
    if (resultText) {
      resultText.textContent = 'Add ?event_id= to the URL after a roll is recorded.';
    }
    return;
  }

  async function fetchResult() {
    const url =
      '/teacher/api/behavior/' +
      classId +
      '/display-result/' +
      eventId;
    const r = await fetch(url, { credentials: 'same-origin' });
    return r.json();
  }

  function animateRoll(finalNum, desc, isNothing) {
    cube.classList.add('rolling');
    let ticks = 0;
    const maxTicks = 18;
    const timer = setInterval(function () {
      ticks++;
      faceNum.textContent = String(Math.floor(Math.random() * 6) + 1);
      if (ticks >= maxTicks) {
        clearInterval(timer);
        cube.classList.remove('rolling');
        faceNum.textContent = String(finalNum);
        resultText.textContent = desc || 'Sentence applied.';
        resultText.classList.toggle('nothing', !!isNothing);
      }
    }, 80);
  }

  fetchResult()
    .then(function (data) {
      if (!data.success) {
        resultText.textContent = data.message || 'Could not load result.';
        return;
      }
      const n = data.die_roll_result || data.second_die_roll || '?';
      animateRoll(
        typeof n === 'number' ? n : 1,
        data.description || '',
        !!data.is_nothing
      );
    })
    .catch(function () {
      resultText.textContent = 'Network error.';
    });
})();
