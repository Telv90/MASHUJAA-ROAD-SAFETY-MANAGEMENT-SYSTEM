(() => {
  const chartDataElement = document.getElementById("chart-data");
  const chartVisualizations = {};
  if (chartDataElement) {
    const data = JSON.parse(chartDataElement.textContent);
    chartVisualizations.trend = drawChart("trend-chart", data.monthly, "line");
    chartVisualizations.hotspots = drawChart("hotspot-chart", data.hotspots, "bar");

    const filterForm = document.querySelector(".filter-panel");
    let chartRequest;
    let filterChangeTimer;
    async function refreshCharts() {
      chartRequest?.abort();
      chartRequest = new AbortController();
      const query = new URLSearchParams(new FormData(filterForm));
      try {
        const response = await fetch(`/api/chart-data?${query}`, {
          headers: { Accept: "application/json" },
          signal: chartRequest.signal,
        });
        if (!response.ok) throw new Error("Could not refresh the charts.");
        const updated = await response.json();
        chartVisualizations.trend?.(updated.monthly);
        chartVisualizations.hotspots?.(updated.hotspots);
      } catch (error) {
        if (error.name !== "AbortError") {
          console.error("Chart refresh failed:", error);
        }
      }
    }

    if (filterForm) {
      filterForm.addEventListener("change", () => {
        window.clearTimeout(filterChangeTimer);
        filterChangeTimer = window.setTimeout(refreshCharts, 180);
      });
      window.setInterval(() => {
        if (!document.hidden) refreshCharts();
      }, 30000);
    }
  }

  const mapElement = document.getElementById("hotspot-map");
  const mapDataElement = document.getElementById("map-data");
  if (mapElement && mapDataElement) {
    if (!window.L) {
      mapElement.textContent = "The map library could not be loaded. Check your internet connection and refresh.";
    } else {
      const points = JSON.parse(mapDataElement.textContent);
      const map = window.L.map(mapElement).setView([-0.8, 37.9], 6);
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);

      const bounds = [];
      points.forEach((point) => {
        const marker = window.L.circleMarker(
          [point.latitude, point.longitude],
          {
            radius: 8,
            color: point.fatalities > 0 ? "#171717" : "#004d2c",
            weight: 2,
            fillColor: point.fatalities > 0 ? "#b5121b" : "#27865c",
            fillOpacity: 0.8,
          },
        ).addTo(map);
        const popup = document.createElement("div");
        const title = document.createElement("strong");
        title.textContent = point.location || "Unspecified location";
        popup.append(title);
        const details = document.createElement("div");
        details.textContent = `${point.road} · ${point.county}`;
        popup.append(details);
        const severity = document.createElement("div");
        severity.textContent = `Fatalities: ${point.fatalities}`;
        popup.append(severity);
        marker.bindPopup(popup);
        bounds.push([point.latitude, point.longitude]);
      });
      if (bounds.length > 1) map.fitBounds(bounds, { padding: [24, 24], maxZoom: 12 });
      else if (bounds.length === 1) map.setView(bounds[0], 12);
    }
  }

  const pickerElement = document.getElementById("coordinate-picker");
  if (pickerElement) {
    if (!window.L) {
      pickerElement.textContent = "The coordinate map could not be loaded. Enter coordinates manually below.";
    } else {
      const latitudeInput = document.getElementById("latitude");
      const longitudeInput = document.getElementById("longitude");
      const lat = Number.parseFloat(latitudeInput.value);
      const lng = Number.parseFloat(longitudeInput.value);
      const hasCoordinates = Number.isFinite(lat) && Number.isFinite(lng);
      const map = window.L.map(pickerElement).setView(
        hasCoordinates ? [lat, lng] : [-0.8, 37.9],
        hasCoordinates ? 12 : 6,
      );
      window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);
      let marker = hasCoordinates
        ? window.L.marker([lat, lng]).addTo(map)
        : null;
      function setLocation(latitude, longitude, zoom) {
        const selected = [latitude, longitude];
        latitudeInput.value = latitude.toFixed(6);
        longitudeInput.value = longitude.toFixed(6);
        map.setView(selected, zoom);
        if (marker) marker.setLatLng(selected);
        else marker = window.L.marker(selected).addTo(map);
      }
      map.on("click", (event) => {
        setLocation(event.latlng.lat, event.latlng.lng, map.getZoom());
      });

      const findButton = document.getElementById("find-location");
      findButton?.addEventListener("click", async () => {
        const query = document.getElementById("map-location-search").value.trim();
        const status = document.getElementById("location-search-status");
        if (query.length < 3) {
          status.textContent = "Enter at least 3 characters.";
          return;
        }
        findButton.disabled = true;
        status.textContent = "Searching OpenStreetMap…";
        try {
          const response = await fetch(`/api/geocode?q=${encodeURIComponent(query)}`);
          const result = await response.json();
          if (!response.ok) throw new Error(result.error || "Location search failed.");
          setLocation(result.latitude, result.longitude, 15);
          status.textContent = result.display_name;
        } catch (error) {
          status.textContent = error.message;
        } finally {
          findButton.disabled = false;
        }
      });
    }
  }

  const signalButton = document.getElementById("load-public-signals");
  if (signalButton) {
    signalButton.addEventListener("click", async () => {
      const status = document.getElementById("public-signals-status");
      const list = document.getElementById("public-signals-list");
      const endpoint = JSON.parse(
        document.getElementById("public-signals-url").textContent,
      );
      signalButton.disabled = true;
      status.textContent = "Fetching configured public sources…";
      list.replaceChildren();
      try {
        const response = await fetch(endpoint, {
          headers: { Accept: "application/json" },
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "Source fetch failed.");
        status.textContent = `Fetched ${payload.signals.length} signal(s) at ${new Date(payload.fetched_at).toLocaleString()}.`;
        payload.signals.forEach((signal) => {
          const card = document.createElement("article");
          card.className = "signal-card";
          const heading = document.createElement("strong");
          heading.textContent = `${signal.platform} · ${signal.source}`;
          card.append(heading);
          const text = document.createElement("p");
          text.textContent = signal.error || signal.text || "No public updates found.";
          card.append(text);
          if (signal.published) {
            const published = document.createElement("small");
            published.textContent = signal.published;
            card.append(published);
          }
          list.append(card);
        });
        if (!payload.signals.length) {
          status.textContent = "No sources are configured yet. Ask an administrator to configure approved handles or official RSS feeds.";
        }
      } catch (error) {
        status.textContent = error.message;
      } finally {
        signalButton.disabled = false;
      }
    });
  }

  const aiButton = document.getElementById("run-ai-analysis");
  if (aiButton) {
    aiButton.addEventListener("click", async () => {
      const status = document.getElementById("ai-analysis-status");
      const results = document.getElementById("ai-analysis-results");
      const csrfToken = document.querySelector(
        'form[action$="/logout"] input[name="csrf_token"]',
      )?.value;
      aiButton.disabled = true;
      status.textContent = "Analyzing recorded aggregates…";
      results.replaceChildren();
      try {
        const response = await fetch("/api/ai-analysis", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "X-CSRF-Token": csrfToken || "",
          },
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.error || "AI analysis failed.");

        const summary = document.createElement("p");
        summary.className = "ai-analysis-summary";
        summary.textContent = payload.analysis.summary;
        results.append(summary);
        payload.analysis.future_hotspots.forEach((hotspot) => {
          const card = document.createElement("article");
          card.className = "recommendation-card";
          const title = document.createElement("h3");
          title.textContent = `${hotspot.location}, ${hotspot.county}`;
          const projection = document.createElement("p");
          projection.textContent = `${hotspot.expected_incidents} expected incidents · ${hotspot.confidence} confidence`;
          const rationale = document.createElement("p");
          rationale.textContent = hotspot.rationale;
          card.append(title, projection, rationale);
          results.append(card);
        });
        payload.analysis.likely_causes.forEach((finding) => {
          const card = document.createElement("article");
          card.className = "recommendation-card";
          const title = document.createElement("h3");
          title.textContent = finding.cause;
          const evidence = document.createElement("p");
          evidence.textContent = finding.evidence;
          const confidence = document.createElement("small");
          confidence.textContent = `Confidence: ${finding.confidence}`;
          card.append(title, evidence, confidence);
          results.append(card);
        });
        payload.analysis.actions.forEach((suggestion) => {
          const card = document.createElement("article");
          card.className = "recommendation-card";
          const title = document.createElement("h3");
          title.textContent = suggestion.action;
          const reason = document.createElement("p");
          reason.textContent = suggestion.reason;
          const priority = document.createElement("small");
          priority.textContent = `Priority: ${suggestion.priority}`;
          card.append(title, reason, priority);
          results.append(card);
        });
        const limitation = document.createElement("p");
        limitation.className = "disclaimer";
        limitation.textContent = payload.analysis.limitations;
        results.append(limitation);
        status.textContent = `Analyzed ${payload.evidence.record_count} incident records.`;
      } catch (error) {
        status.textContent = error.message;
      } finally {
        aiButton.disabled = false;
      }
    });
  }

  function drawChart(id, series, type) {
    const canvas = document.getElementById(id);
    if (!canvas) return;
    const context = canvas.getContext("2d");
    let labels = Array.isArray(series.labels) ? series.labels : [];
    let values = Array.isArray(series.values) ? series.values : [];
    let fatalIncidents = Array.isArray(series.fatal_incidents)
      ? series.fatal_incidents
      : [];
    const tooltip = document.createElement("div");
    tooltip.className = "chart-tooltip";
    tooltip.setAttribute("role", "status");
    tooltip.setAttribute("aria-live", "polite");
    tooltip.hidden = true;
    canvas.parentElement.append(tooltip);

    let hoveredIndex = -1;
    let animationFrame = 0;
    let animationStart = 0;
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;

    function render(progress = 1) {
      const ratio = window.devicePixelRatio || 1;
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      if (!width || !height) return;
      canvas.width = Math.round(width * ratio);
      canvas.height = Math.round(height * ratio);
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
      context.clearRect(0, 0, width, height);

      if (!labels.length || !values.length) {
        context.fillStyle = "#89928d";
        context.font = "12px sans-serif";
        context.textAlign = "center";
        context.fillText("No incident data in this view", width / 2, height / 2);
        return;
      }

      const padding = { top: 12, right: 12, bottom: 43, left: 31 };
      const chartWidth = width - padding.left - padding.right;
      const chartHeight = height - padding.top - padding.bottom;
      const maxValue = Math.max(1, ...values);
      context.font = "10px sans-serif";
      context.textAlign = "right";
      for (let tick = 0; tick <= 3; tick += 1) {
        const y = padding.top + (chartHeight * tick) / 3;
        context.strokeStyle = "#edf0ed";
        context.beginPath();
        context.moveTo(padding.left, y);
        context.lineTo(width - padding.right, y);
        context.stroke();
        context.fillStyle = "#89928d";
        context.fillText(
          String(Math.round(maxValue * (3 - tick) / 3)),
          padding.left - 7,
          y + 3,
        );
      }

      if (type === "line") {
        const points = values.map((value, index) => ({
          x: padding.left + (labels.length === 1
            ? chartWidth / 2
            : (chartWidth * index) / (labels.length - 1)),
          y: padding.top + chartHeight
            - (chartHeight * value * progress) / maxValue,
        }));
        const pointDepth = (index) =>
          Math.min(14, 4 + (fatalIncidents[index] || 0) * 2);
        context.strokeStyle = "#b9c9c0";
        context.lineWidth = 1;
        context.beginPath();
        points.forEach((point, index) => {
          const depth = pointDepth(index);
          if (index === 0) {
            context.moveTo(point.x + depth, point.y - depth * 0.8);
          } else {
            context.lineTo(point.x + depth, point.y - depth * 0.8);
          }
        });
        context.stroke();
        points.forEach((point, index) => {
          const depth = pointDepth(index);
          context.beginPath();
          context.moveTo(point.x, point.y);
          context.lineTo(point.x + depth, point.y - depth * 0.8);
          context.stroke();
        });
        context.strokeStyle = "#247652";
        context.lineWidth = 2;
        context.beginPath();
        points.forEach((point, index) => {
          if (index === 0) context.moveTo(point.x, point.y);
          else context.lineTo(point.x, point.y);
        });
        context.stroke();
        points.forEach((point, index) => {
          context.beginPath();
          context.arc(point.x, point.y, index === hoveredIndex ? 5 : 3, 0, Math.PI * 2);
          context.fillStyle = index === hoveredIndex ? "#b5121b" : "#247652";
          context.fill();
        });
      } else {
        const slot = chartWidth / labels.length;
        const barWidth = Math.min(28, slot * 0.58);
        values.forEach((value, index) => {
          const barHeight = (chartHeight * value * progress) / maxValue;
          const x = padding.left + slot * index + (slot - barWidth) / 2;
          const y = padding.top + chartHeight - barHeight;
          const depthX = Math.min(
            20, 5 + (fatalIncidents[index] || 0) * 3,
          );
          const depthY = depthX * 0.8;
          const color = index === hoveredIndex ? "#247652" : "#b5121b";
          context.fillStyle = color;
          context.fillRect(x, y, barWidth, barHeight);
          context.beginPath();
          context.moveTo(x, y);
          context.lineTo(x + depthX, y - depthY);
          context.lineTo(x + barWidth + depthX, y - depthY);
          context.lineTo(x + barWidth, y);
          context.closePath();
          context.fillStyle = index === hoveredIndex ? "#4b9674" : "#d65a5f";
          context.fill();
          context.beginPath();
          context.moveTo(x + barWidth, y);
          context.lineTo(x + barWidth + depthX, y - depthY);
          context.lineTo(x + barWidth + depthX, y + barHeight - depthY);
          context.lineTo(x + barWidth, y + barHeight);
          context.closePath();
          context.fillStyle = index === hoveredIndex ? "#175239" : "#861018";
          context.fill();
        });
      }

      const labelStep = Math.max(1, Math.ceil(labels.length / 6));
      context.fillStyle = "#77827c";
      context.textAlign = "center";
      labels.forEach((label, index) => {
        if (index % labelStep !== 0 && index !== labels.length - 1) return;
        const x = type === "line"
          ? padding.left + (labels.length === 1
            ? chartWidth / 2
            : (chartWidth * index) / (labels.length - 1))
          : padding.left + chartWidth * (index + 0.5) / labels.length;
        const shortLabel = label.length > 12 ? `${label.slice(0, 11)}…` : label;
        context.save();
        context.translate(x, height - 6);
        if (type === "bar" && labels.length > 4) context.rotate(-0.35);
        context.fillText(shortLabel, 0, 0);
        context.restore();
      });
    }

    function animate(timestamp) {
      if (!animationStart) animationStart = timestamp;
      const progress = Math.min(1, (timestamp - animationStart) / 550);
      render(1 - ((1 - progress) ** 3));
      if (progress < 1) animationFrame = window.requestAnimationFrame(animate);
    }

    function startAnimation() {
      window.cancelAnimationFrame(animationFrame);
      animationStart = 0;
      if (prefersReducedMotion) {
        render();
      } else {
        animationFrame = window.requestAnimationFrame(animate);
      }
    }

    function update(nextSeries) {
      labels = Array.isArray(nextSeries.labels) ? nextSeries.labels : [];
      values = Array.isArray(nextSeries.values) ? nextSeries.values : [];
      fatalIncidents = Array.isArray(nextSeries.fatal_incidents)
        ? nextSeries.fatal_incidents
        : [];
      hoveredIndex = -1;
      tooltip.hidden = true;
      startAnimation();
    }

    canvas.addEventListener("pointermove", (event) => {
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const padding = { left: 31, right: 12 };
      const chartWidth = rect.width - padding.left - padding.right;
      if (chartWidth <= 0 || !labels.length) return;
      const nextIndex = type === "line"
        ? Math.max(0, Math.min(
          labels.length - 1,
          Math.round(((x - padding.left) / chartWidth) * (labels.length - 1)),
        ))
        : Math.max(0, Math.min(
          labels.length - 1,
          Math.floor(((x - padding.left) / chartWidth) * labels.length),
        ));
      if (nextIndex === hoveredIndex) return;
      hoveredIndex = nextIndex;
      const fatalCount = fatalIncidents[nextIndex] || 0;
      tooltip.textContent = `${labels[nextIndex]}: ${values[nextIndex]} incident${values[nextIndex] === 1 ? "" : "s"} · ${fatalCount} fatal incident${fatalCount === 1 ? "" : "s"}`;
      tooltip.hidden = false;
      tooltip.style.left = `${Math.max(8, Math.min(rect.width - 190, x + 12))}px`;
      tooltip.style.top = `${Math.max(4, event.clientY - rect.top - 34)}px`;
      render();
    });

    canvas.addEventListener("pointerleave", () => {
      hoveredIndex = -1;
      tooltip.hidden = true;
      render();
    });
    canvas.addEventListener("focus", startAnimation);
    if (window.ResizeObserver) {
      new ResizeObserver(startAnimation).observe(canvas);
    } else {
      window.addEventListener("resize", startAnimation);
    }
    startAnimation();
    return update;
  }
})();
