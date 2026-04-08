use pyo3::prelude::*;
use fuzzy_matcher::skim::SkimMatcherV2;
use fuzzy_matcher::FuzzyMatcher;
use std::collections::{HashMap, HashSet};

#[pyfunction]
fn fuzzy_search(query: &str, data: Vec<String>, limit: usize) -> Vec<String> {
    let matcher = SkimMatcherV2::default();

    let mut results: Vec<(i64, String)> = data
        .into_iter()
        .filter_map(|item| {
            matcher
                .fuzzy_match(&item.to_lowercase(), &query.to_lowercase())
                .map(|score| (score, item))
        })
        .collect();

    // сортировка по релевантности
    results.sort_by(|a, b| b.0.cmp(&a.0));

    results
        .into_iter()
        .take(limit)
        .map(|(_, item)| item)
        .collect()
}

#[pyfunction]
fn employees_count(data: Vec<String>) -> (usize, usize) {
    let total = data.len();

    let unique: HashSet<String> = data.into_iter().collect();
    let unique_count = unique.len();

    (total, unique_count)
}


#[pymodule]
fn rust_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fuzzy_search, m)?)?;
    m.add_function(wrap_pyfunction!(employees_count, m)?)?;
    Ok(())
}
