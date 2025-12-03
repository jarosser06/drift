# Release Skill

Guide the user through the process of releasing a new version of the ai-drift package to PyPI.

## Process

1. **Determine bump type**: Ask the user which type of version bump to perform:
   - `major` - Breaking changes (e.g., 1.0.0 → 2.0.0)
   - `minor` - New features, backward compatible (e.g., 0.1.0 → 0.2.0)
   - `patch` - Bug fixes, backward compatible (e.g., 0.1.1 → 0.1.2)

2. **Run bump-version script**: Execute `./scripts/bump-version.sh {bump_type} --no-changelog` to:
   - Update version in `pyproject.toml`
   - Capture the new version number from stdout

3. **Show version change**: Display the version change to the user (old → new)

4. **Ask for changelog description**: Prompt the user to describe the changes in this release. This should be a concise summary of:
   - New features added
   - Bugs fixed
   - Breaking changes (if major bump)
   - Other notable changes

   Format: Single line or bullet points

5. **Update changelog**: Run `./scripts/update-changelog.sh {version} "{description}"` to add the entry to CHANGELOG.md

6. **Show git diff**: Display the changes made by running `git diff` so the user can review

7. **Commit changes**: Create a commit with the version bump:
   ```bash
   git add .
   git commit -m "chore: release v{version}"
   ```

8. **Create git tag**: Create an annotated tag for the release:
   ```bash
   git tag -a v{version} -m "Release v{version}"
   ```

9. **Confirm push**: Ask the user if they want to push the commit and tag now.

10. **Push if confirmed**: If the user confirms, push both the commit and tags:
    ```bash
    git push && git push --tags
    ```

11. **Build and publish**: Ask if they want to build and publish to PyPI now:
    - If yes, run `./distro.sh build --clean`
    - Ask if they want to test on TestPyPI first
    - If testing: run `./distro.sh push --test`
    - If ready for production: run `./distro.sh push`

12. **Inform about GitHub Release**: Remind the user they can create a GitHub Release manually at:
    https://github.com/jarosser06/drift/releases/new
    - Select tag: v{version}
    - Use CHANGELOG entry as description
    - Can attach distribution files from `dist/` if desired

## Important Notes

- The version format is `MAJOR.MINOR.PATCH` (SemVer)
- Tags use the format `v{version}` (e.g., `v0.2.0`)
- The bump-version script updates pyproject.toml automatically
- Always verify the git diff before committing
- PyPI does not allow replacing versions - must bump to publish updates
- The PyPI package page will automatically update with new README content

## Example Flow

```
User: /release
Assistant: Which type of version bump do you want to perform?
- major (breaking changes)
- minor (new features)
- patch (bug fixes)

User: minor
Assistant: [Runs ./scripts/bump-version.sh minor --no-changelog]
Bumping version: 0.1.1 → 0.2.0

Please describe the changes in this release:

User: Added support for X, fixed bug in Y
Assistant: [Runs ./scripts/update-changelog.sh 0.2.0 "Added support for X, fixed bug in Y"]
[Shows git diff]

Ready to commit and tag? (yes/no)

User: yes
Assistant: [Creates commit and tag]
Do you want to push now? (yes/no)

User: yes
Assistant: [Pushes commit and tags]

Do you want to build and publish to PyPI now? (yes/no)

User: yes
Assistant: [Runs ./distro.sh build --clean]
Do you want to test on TestPyPI first? (yes/no)

User: no
Assistant: [Runs ./distro.sh push]
Release v0.2.0 has been published to PyPI!

You can create a GitHub Release at:
https://github.com/jarosser06/drift/releases/new
```
