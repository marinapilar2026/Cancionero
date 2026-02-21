(function () {
  const listEl = document.getElementById("songList");
  const statusEl = document.getElementById("status");
  const viewEl = document.getElementById("songView");
  const titleEl = document.getElementById("songTitle");
  const bodyEl = document.getElementById("songBody");
  const searchInput = document.getElementById("searchInput");
  const countEl = document.getElementById("count");

  let songs = [];
  let filteredSongs = [];
  let currentId = null;

  function setStatus(msg) {
    statusEl.textContent = msg;
  }

  function normalize(text) {
    return (text || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/\p{Diacritic}/gu, "");
  }

  function renderList() {
    listEl.innerHTML = "";

    filteredSongs.forEach((song) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "song-item";
      if (song.id === currentId) btn.classList.add("active");
      btn.textContent = `${song.number}. ${song.title}`;
      btn.addEventListener("click", () => selectSong(song.id));
      listEl.appendChild(btn);
    });

    countEl.textContent = `${filteredSongs.length} / ${songs.length}`;
  }

  function selectSong(id) {
    const song = songs.find((s) => s.id === id);
    if (!song) return;

    currentId = id;
    titleEl.textContent = `${song.number}. ${song.title}`;
    bodyEl.textContent = song.body || "";
    viewEl.hidden = false;
    renderList();
  }

  function applyFilter() {
    const q = normalize(searchInput.value.trim());

    if (!q) {
      filteredSongs = songs.slice();
      renderList();
      return;
    }

    filteredSongs = songs.filter((song) => {
      const haystack = `${normalize(song.title)}\n${normalize(song.body)}`;
      return haystack.includes(q);
    });

    if (filteredSongs.length && !filteredSongs.some((s) => s.id === currentId)) {
      selectSong(filteredSongs[0].id);
    } else {
      renderList();
    }

    if (!filteredSongs.length) {
      setStatus("No hay coincidencias.");
      viewEl.hidden = true;
    } else {
      setStatus("Listo.");
      viewEl.hidden = false;
    }
  }

  async function loadSongs() {
    try {
      setStatus("Cargando canciones...");
      const indexResp = await fetch("songs/index.json", { cache: "no-store" });
      if (!indexResp.ok) throw new Error("No se pudo abrir songs/index.json");

      const index = await indexResp.json();
      songs = await Promise.all(
        index.map(async (meta) => {
          const resp = await fetch(`songs/${meta.file}`, { cache: "no-store" });
          const rawBody = resp.ok ? await resp.text() : "";
          const body = rawBody.replace(/^\uFEFF/, "").trim();
          return { ...meta, body };
        })
      );

      filteredSongs = songs.slice();
      renderList();

      if (songs.length) {
        selectSong(songs[0].id);
        setStatus("Listo.");
      } else {
        setStatus("No hay canciones cargadas.");
      }
    } catch (err) {
      console.error(err);
      setStatus("Error cargando canciones. Verifica songs/index.json y los .txt en songs/.");
    }
  }

  searchInput.addEventListener("input", applyFilter);
  loadSongs();
})();
