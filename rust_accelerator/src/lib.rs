use pyo3::prelude::*;
use numpy::{PyReadonlyArray1, PyReadonlyArray2, IntoPyArray};
use rayon::prelude::*;
use tokenizers::Tokenizer;
use dashmap::DashMap;
use std::sync::Arc;
use serde::{Deserialize, Serialize};

#[pyclass]
pub struct FastVectorEngine {}

#[pymethods]
impl FastVectorEngine {
    #[new]
    fn new() -> Self {
        FastVectorEngine {}
    }

    /// Computes cosine similarity between a 1D query and a 2D matrix of target vectors.
    fn batch_cosine_similarity<'py>(
        &self,
        py: Python<'py>,
        query: PyReadonlyArray1<f32>,
        targets: PyReadonlyArray2<f32>,
    ) -> PyResult<pyo3::Bound<'py, numpy::PyArray1<f32>>> {
        let q = query.as_slice()?;
        let t = targets.as_array();
        
        let similarities: Vec<f32> = t.axis_iter(ndarray::Axis(0))
            .into_par_iter()
            .map(|row| {
                let r = row.as_slice().unwrap();
                let mut dot = 0.0;
                let mut mag_q_sq = 0.0;
                let mut mag_r_sq = 0.0;
                
                for (a, b) in q.iter().zip(r.iter()) {
                    dot += a * b;
                    mag_q_sq += a * a;
                    mag_r_sq += b * b;
                }
                
                let mag_q = mag_q_sq.sqrt();
                let mag_r = mag_r_sq.sqrt();
                
                if mag_q * mag_r == 0.0 { 0.0 } else { dot / (mag_q * mag_r) }
            })
            .collect();
            
        Ok(similarities.into_pyarray_bound(py))
    }

    /// Ranks top-K indices based on cosine similarity.
    fn rank_top_k(&self, query: PyReadonlyArray1<f32>, targets: PyReadonlyArray2<f32>, k: usize) -> PyResult<Vec<(usize, f32)>> {
        let q = query.as_slice()?;
        let t = targets.as_array();
        
        let mut scores: Vec<(usize, f32)> = t.axis_iter(ndarray::Axis(0))
            .into_par_iter()
            .enumerate()
            .map(|(idx, row)| {
                let r = row.as_slice().unwrap();
                let mut dot = 0.0;
                let mut mag_q_sq = 0.0;
                let mut mag_r_sq = 0.0;
                for (a, b) in q.iter().zip(r.iter()) {
                    dot += a * b;
                    mag_q_sq += a * a;
                    mag_r_sq += b * b;
                }
                let sim = if mag_q_sq * mag_r_sq == 0.0 { 0.0 } else { dot / (mag_q_sq.sqrt() * mag_r_sq.sqrt()) };
                (idx, sim)
            })
            .collect();

        // Sort by score descending
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        
        Ok(scores.into_iter().take(k).collect())
    }
}

#[pyclass]
pub struct RustTokenizer {
    tokenizer: Tokenizer,
}

#[pymethods]
impl RustTokenizer {
    #[new]
    fn new(path: String) -> PyResult<Self> {
        let tokenizer = Tokenizer::from_file(path).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(RustTokenizer { tokenizer })
    }

    fn encode(&self, text: String) -> PyResult<Vec<u32>> {
        let encoding = self.tokenizer.encode(text, true).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(encoding.get_ids().to_vec())
    }

    fn decode(&self, ids: Vec<u32>) -> PyResult<String> {
        let decoding = self.tokenizer.decode(&ids, true).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(decoding)
    }

    fn count_tokens(&self, text: String) -> PyResult<usize> {
        let encoding = self.tokenizer.encode(text, true).map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(encoding.get_ids().len())
    }
}

#[pyclass]
pub struct EmbeddingCache {
    cache: DashMap<String, Vec<f32>>,
}

#[pymethods]
impl EmbeddingCache {
    #[new]
    fn new() -> Self {
        EmbeddingCache {
            cache: DashMap::new(),
        }
    }

    fn get(&self, key: String) -> Option<Vec<f32>> {
        self.cache.get(&key).map(|v| v.value().clone())
    }

    fn set(&self, key: String, vector: Vec<f32>) {
        self.cache.insert(key, vector);
    }

    fn clear(&self) {
        self.cache.clear();
    }

    fn size(&self) -> usize {
        self.cache.len()
    }
}

#[pyclass]
pub struct ParallelOrchestrator {
    runtime: tokio::runtime::Runtime,
    client: reqwest::Client,
}

#[pymethods]
impl ParallelOrchestrator {
    #[new]
    fn new() -> PyResult<Self> {
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(ParallelOrchestrator {
            runtime,
            client: reqwest::Client::new(),
        })
    }

    fn request_batch<'py>(&self, py: Python<'py>, urls: Vec<String>, payloads: Vec<String>) -> PyResult<Vec<String>> {
        let client = self.client.clone();
        
        self.runtime.block_on(async move {
            let mut futures = Vec::new();
            for (url, payload) in urls.into_iter().zip(payloads.into_iter()) {
                let client = client.clone();
                futures.push(tokio::spawn(async move {
                    let resp = client.post(url)
                        .header("Content-Type", "application/json")
                        .body(payload)
                        .send()
                        .await;
                    
                    match resp {
                        Ok(r) => r.text().await.unwrap_or_else(|_| "Error reading text".to_string()),
                        Err(e) => format!("Error: {}", e),
                    }
                }));
            }

            let mut results = Vec::new();
            for f in futures {
                results.push(f.await.unwrap_or_else(|_| "Task panicked".to_string()));
            }
            Ok(results)
        })
    }
}

#[pymodule]
fn rust_accelerator(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<FastVectorEngine>()?;
    m.add_class::<RustTokenizer>()?;
    m.add_class::<EmbeddingCache>()?;
    m.add_class::<ParallelOrchestrator>()?;
    Ok(())
}
