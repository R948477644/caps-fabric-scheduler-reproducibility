# Release Checklist

Use this checklist before submitting to PeerJ Computer Science.

1. Create a public GitHub repository.
2. Push this repository to GitHub.
3. Check that `README.md`, `REPRODUCIBILITY.md`, `DATA.md`, `LICENSE`, and
   `CITATION.cff` render correctly.
4. Create a GitHub release named `v1.0.0-peerj-submission`.
5. Attach any large raw-data archives that should not live in git history.
6. Connect the GitHub repository to Zenodo.
7. Archive the release on Zenodo and obtain a DOI.
8. Replace placeholders in `README.md`, `CITATION.cff`, and the manuscript Data
   Availability statement:

```text
GITHUB_RELEASE_URL
ZENODO_DOI
https://github.com/USERNAME/caps-fabric-scheduler-reproducibility
```

9. Rebuild the manuscript PDF after replacing placeholders.
