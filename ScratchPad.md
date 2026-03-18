Perform a final, "zero-failure" audit of the latest code changes. Do not allow a push to the repository if any of the following criteria are failed. 
Phase 1: Technical & Security AuditLogic & Regressions: Identify every touchpoint where new changes interact with existing modules. Highlight potential side effects or "ripple" bugs. Security: Check for XSS, CSRF, or insecure data handling in both Frontend and Backend. Performance: Audit for inefficient loops, unnecessary re-renders, or heavy payloads.
Phase 2: UI & WCAG 2.1 AA Compliance Semantic HTML: Ensure correct use of landmarks (header, main, nav) and heading levels ($H1$ through $H6$). Interactivity: Verify that all new components are fully keyboard-navigable (Tab order, Focus states). Attributes: Check for missing aria-labels, alt text, and associated form labels. Visuals: Audit colour contrast ratios (minimum 4.5:1 for normal text) and ensure no information is conveyed by colour alone.
Phase 3: Adversarial Review, Identify three edge cases where these changes will break for a user—one for a screen reader user, one for a mobile user, and one for a low-bandwidth user. Final Output: Provide a "Go/No-Go" status. For every "No-Go," provide the file name, line number, and the specific WCAG success criterion or logic principle violated.

Once done push to the repo, using /deploy please.   


TD List
- Need to add a link to the post in the engagement list so I can verify the DM reference is correct. Also a time since reply so I can see how immediate the DM will be.
- Some of the post links when approving just go to a picture or video. We need to ALWAYS link to the post and not the picture or video.
- Refator to the cloudflare version of the app and maximum optimisation for mobile UX and performance. Maybe as a PWA.
- 


