import {expandData} from "./data.js";
import {initializeApp} from "./app.js";


document.addEventListener("DOMContentLoaded", async function () {
    const testSuiteDescirptors = {"HighVertexCountTests": {"class_name": "HighVertexCountTests", "description": ["Tests behavior when large numbers of vertices are specified without an END call."], "source_file": "https://github.com/abaire/xemu-perf-tests/blob/main/src/tests/high_vertex_count_tests.h", "tests": {"HighVtxCount-arrays": "Tests NV097_DRAW_ARRAYS with a very large number of vertices.", "HighVtxCount-inlinearrays": "Tests NV097_INLINE_ARRAY with a very large number of vertices.", "HighVtxCount-inlinebuffers": "Tests immediate mode (e.g., NV097_SET_VERTEX3F) with a very large number of vertices.", "HighVtxCount-inlineelements": "Tests NV097_ARRAY_ELEMENT16 / NV097_ARRAY_ELEMENT32 with a very large number of vertices. "}}, "VertexBufferAllocationTests": {"class_name": "VertexBufferAllocationTests", "description": ["Tests behavior of pathological xemu GL buffer allocations due to use of certain vertex specification methods."], "source_file": "https://github.com/abaire/xemu-perf-tests/blob/main/src/tests/vertex_buffer_allocation_tests.h", "tests": {"MixedVtxAlloc-arrays": "Tests NV097_DRAW_ARRAYS with multiple successive draws using a variety of different vertex counts.", "MixedVtxAlloc-inlinearrays": "Tests NV097_INLINE_ARRAY with multiple successive draws using a variety of different vertex counts.", "MixedVtxAlloc-inlinebuffers": "Tests immediate mode (e.g., NV097_SET_VERTEX3F) with multiple successive draws using a variety of different vertex counts.", "MixedVtxAlloc-inlineelements": "Tests NV097_ARRAY_ELEMENT16 / NV097_ARRAY_ELEMENT32 with multiple successive draws using a variety of different vertex counts.", "TinyAlloc-arrays": "Tests NV097_DRAW_ARRAYS with a large number of single quad draws.", "TinyAlloc-inlinearrays": "Tests NV097_INLINE_ARRAY with a large number of single quad draws.", "TinyAlloc-inlinebuffers": "Tests immediate mode (e.g., NV097_SET_VERTEX3F) with a large number of single quad draws.", "TinyAlloc-inlineelements": "Tests NV097_ARRAY_ELEMENT16 / NV097_ARRAY_ELEMENT32 with a large number of single quad draws. "}}};
    const loadingContainer = document.getElementById("loading-container");
    const chartsContainer = document.getElementById("charts-container");

    function displayError(error) {
        console.error("Failed to load data:", error);
        loadingContainer.innerHTML = '<p style="color: red;">Error: Could not load data.</p>';
    }

    try {
        const response = await fetch("results.json.gz");
        if (!response.ok) {
            displayError(`Data load failed: HTTP ${response.status}`)
            return;
        }

        const contentEncoding = response.headers.get("Content-Encoding");
        const contentType = response.headers.get("Content-Type");

        const likelyCompressed = contentType.includes("gzip") || contentType.includes("x-gzip") || response.url.endsWith(".gz");

        let data;
        if (contentEncoding === "gzip" || !likelyCompressed) {
            data = await response.json();
        } else {
            const compressedData = await response.arrayBuffer();
            const decompressedData = pako.inflate(compressedData, {to: "string"});
            data = JSON.parse(decompressedData);
        }

        data = expandData(data);

        loadingContainer.style.display = "none";
        chartsContainer.style.display = "block";

        initializeApp(data, testSuiteDescirptors);
    } catch (error) {
        displayError(error);
    }
});
