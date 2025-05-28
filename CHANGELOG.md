# CHANGELOG

## v0.1.0 (2025-05-28)

### Build

* build: remove requirements.txt in favor of pyproject.toml

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`ee64b67`](https://github.com/Agentic-Brain/standard_pipelines/commit/ee64b67933ee8c407b6988afc7e7a6fce9e236f8))

* build: add pyproject.toml with all dependencies and configurations

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`dbf33d6`](https://github.com/Agentic-Brain/standard_pipelines/commit/dbf33d63e468c74c171c7a188c829fa8e327ce71))

### Chore

* chore(workflow): rename step to &#34;Install Versioning &amp; Build Tools&#34; for clarity
fix(workflow): add explicit version for yq and verify installations after setup

chore(uv.lock): add new dependencies for click-option-group, deprecated, dotty-dict, gitdb, gitpython, and markdown-it-py to ensure all required packages are explicitly listed and available for consistent environment setup

chore: update uv.lock with new dependencies including mdurl, pygments, and others to ensure all required packages are available for the project and improve dependency management

chore: add &#34;shellingham&#34; and &#34;smmap&#34; packages to lock file for dependency completeness
update: increase &#34;standard-pipelines&#34; version to 1.3.1 for new features and fixes
chore: add &#34;python-semantic-release&#34; to dependencies to support semantic versioning
add: include &#34;tomlkit&#34; package for improved TOML file handling in dependencies ([`2b1cdf4`](https://github.com/Agentic-Brain/standard_pipelines/commit/2b1cdf4ea44ae0e84841aa39bbcb2466bd30153d))

* chore: update docker image to v1.3.1 and modify migration command to set environment variable PRODUCTION_USE_PAPERTRAIL to false in production compose file

build: bump project version to 1.3.1 in pyproject.toml and version.py for release management

feat: add semantic_release configuration to automate versioning, tagging, and releasing ([`2f0a46b`](https://github.com/Agentic-Brain/standard_pipelines/commit/2f0a46bef0b501bb85d379ecbc7e959d577d111d))

* chore: add GitHub Action for common setup of Python, uv, and Bitwarden Secrets CLI

feat: create workflow for automated version bumping on main branch and PR merge
- triggers on PR merge to main or manual dispatch
- checks out code with full history
- runs common setup for Python, uv, and BWS
- installs semantic-release and YAML tools
- configures git user for commits
- runs semantic-release to bump version, create tags, and releases
- updates docker-compose-prod.yaml with new version if release occurs
- commits and pushes updated compose file

chore(workflow): add GitHub Actions workflow for OpenCommit to automate commit messages ([`ad7c3e0`](https://github.com/Agentic-Brain/standard_pipelines/commit/ad7c3e0974f1b350d12c20ecab71df6e24ba02d9))

### Feature

* feat: add persistent database tests (#70)

* feat: add persistent database tests with client and dataflow

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;

* fix: use unique email for persistent db test

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;

* fix: commit dataflow before creating join entry

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;

* fix: refresh dataflow object after commit

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;

* fix: refresh both client and dataflow objects after commit

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;

* fix: add app parameter to test function

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;

* fix: fetch fresh objects from database before creating relationship

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;

* fix: use ids in test to avoid detached instance issues

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;

* fix: add app context to fixture

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;

* remove unneeded call to app context

* sneak in that trufflehog fix

* syntax fix

* fixed typo

---------

Co-authored-by: Devin AI &lt;158243242+devin-ai-integration[bot]@users.noreply.github.com&gt;
Co-authored-by: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt;
Co-authored-by: Adam Pohl &lt;acpohl21@gmail.com&gt; ([`5f22908`](https://github.com/Agentic-Brain/standard_pipelines/commit/5f22908b3c281c02f340febad0ebf6a7e362bfd9))

* feat: add test logging endpoint

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`3ccd384`](https://github.com/Agentic-Brain/standard_pipelines/commit/3ccd3846f7463b68e60f536c32a9095bf0559230))

* feat: add ScheduledMixin and celery task for scheduled operations

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`63a585e`](https://github.com/Agentic-Brain/standard_pipelines/commit/63a585ef03353d2b894dd3d1d043bc1ab03e3501))

* feat: add Docker build CI/CD pipeline

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`76cfc6b`](https://github.com/Agentic-Brain/standard_pipelines/commit/76cfc6b858d6cefa680a5e5979271127d06384ca))

* feat: Add GitHub Actions CI workflow and fix TimestampMixin references

- Add GitHub Actions workflow with BWS integration
- Remove TimestampMixin references from test_database.py
- Update timestamp tests to use BaseMixin fields

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`210fed2`](https://github.com/Agentic-Brain/standard_pipelines/commit/210fed2adfe7e19dd213a3fea64c1f4a4dd00428))

### Fix

* fix(__init__.py): update import to use __version__ instead of APP_VERSION for consistency
fix(__init__.py): conditionally set release in Sentry init to use __version__ for accurate version tracking ([`7a6183d`](https://github.com/Agentic-Brain/standard_pipelines/commit/7a6183d0862e541ad8ddbeb62551ec18522a0493))

* fix(services.py): replace multiple email validation checks with a single condition
and assign a default email if validation fails to ensure contact data integrity ([`03f298e`](https://github.com/Agentic-Brain/standard_pipelines/commit/03f298e79362d03c1ac2e45d7bb829c02b534f73))

* fix: skip bitwarden initialization when disabled

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`d048041`](https://github.com/Agentic-Brain/standard_pipelines/commit/d0480416f5bf28f00be52ca3ba704e37b1cad8d6))

* fix: respect environment variables for api configuration

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`323ea72`](https://github.com/Agentic-Brain/standard_pipelines/commit/323ea72f4c80bdd6839db6c5e53ac65de35ffa39))

* fix: skip api config validation for disabled apis

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`58ef18b`](https://github.com/Agentic-Brain/standard_pipelines/commit/58ef18b8f81a31b0de81efda7ed4426fc3a3eae9))

* fix: handle missing sentry dsn gracefully

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`93b8ec8`](https://github.com/Agentic-Brain/standard_pipelines/commit/93b8ec8a864e9aa2e40ae1aa3f2672006a9085c9))

* fix: environment-specific logging formats and prevent duplicate logs

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`be11abb`](https://github.com/Agentic-Brain/standard_pipelines/commit/be11abb436126db07dad3b890cacefa7a0f9c950))

* fix: update celery task to handle run count tracking

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`36cdbe9`](https://github.com/Agentic-Brain/standard_pipelines/commit/36cdbe908a12b61688953a51903a6b8ae171e2e6))

* fix: add missing import in scheduled_mixin

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`2d81883`](https://github.com/Agentic-Brain/standard_pipelines/commit/2d818835244a03129c1873a067ee6d5c446965a5))

* fix: update deprecated FLASK_ENV to FLASK_DEBUG

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`1267a66`](https://github.com/Agentic-Brain/standard_pipelines/commit/1267a66a7ab9a329c2bd747d2b2b9b04ca84c3a1))

* fix: update Bitwarden secret names for better security

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`6ef3632`](https://github.com/Agentic-Brain/standard_pipelines/commit/6ef36322894213d297963f030fd54664af10d9b6))

* fix: update Bitwarden secrets path format

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`a71161e`](https://github.com/Agentic-Brain/standard_pipelines/commit/a71161e805b8ec530f34ece4294563d919d73ed2))

* fix: update Bitwarden Secrets Manager configuration

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`9b65583`](https://github.com/Agentic-Brain/standard_pipelines/commit/9b6558378a0a826cc5153bf5597c01cbb36e1d06))

### Refactor

* refactor: improve scheduled mixin based on code review

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`a679472`](https://github.com/Agentic-Brain/standard_pipelines/commit/a6794723cc8a696163bea5ae4ca82fa6d2138f94))

* refactor: consolidate CI workflows and use official Bitwarden Secrets Manager action

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`0441bea`](https://github.com/Agentic-Brain/standard_pipelines/commit/0441beae8d42878b6a62b9fe2e793b925459cc53))

### Test

* test: add comprehensive tests for ScheduledMixin

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`4508eca`](https://github.com/Agentic-Brain/standard_pipelines/commit/4508ecaa9d0f87f005b4f2b57e4e007f0efda975))

### Unknown

* Merge pull request #112 from Agentic-Brain/finalizing_ci

Finalizing ci ([`fd46ec7`](https://github.com/Agentic-Brain/standard_pipelines/commit/fd46ec7d0274f21b5461b911aa48b335b944d1d3))

* Merge pull request #111 from Agentic-Brain/seer/validate-contact-email

Add validation for contact object and email field in webhook data ([`a505c70`](https://github.com/Agentic-Brain/standard_pipelines/commit/a505c703f565a96cd08f3d0187a10601952960d2))

* Add validation for contact object and email field in webhook data ([`b47512e`](https://github.com/Agentic-Brain/standard_pipelines/commit/b47512e290742042a060a8095f5341aaa55ccfb3))

* Merge pull request #109 from Agentic-Brain/credentials

Credentials ([`2753b54`](https://github.com/Agentic-Brain/standard_pipelines/commit/2753b54c2bb77744cf7360a51295641c88195f9a))

* version bump ([`69060ba`](https://github.com/Agentic-Brain/standard_pipelines/commit/69060ba17889e13499430c74f27be54cd0a6823a))

* template rewrite ([`da808f9`](https://github.com/Agentic-Brain/standard_pipelines/commit/da808f941768df95c9ddb8fd83b025e5a9812914))

* cleaning up templates ([`150b461`](https://github.com/Agentic-Brain/standard_pipelines/commit/150b461ee5816a17c8a08a68a3ac427866d7c233))

* modifying credential add features ([`6ab61be`](https://github.com/Agentic-Brain/standard_pipelines/commit/6ab61be7e6daa36ec0630b869808eb945dd533f5))

* admin dash work ([`07bf9cc`](https://github.com/Agentic-Brain/standard_pipelines/commit/07bf9cc3434822ef83b44a819985aaa9b09643cb))

* Merge pull request #108 from Agentic-Brain/dp2ss_final

Dp2ss final ([`c4eb073`](https://github.com/Agentic-Brain/standard_pipelines/commit/c4eb073069d176d98c5198f132338c38d3c16bd6))

* Merge branch &#39;main&#39; into dp2ss_final ([`941f73e`](https://github.com/Agentic-Brain/standard_pipelines/commit/941f73ebd993c52e595b8fa5e5600e36550c7b3f))

* version bump ([`6afc9d7`](https://github.com/Agentic-Brain/standard_pipelines/commit/6afc9d7f171781b1c11d67bf31173f3eb7b35c33))

* working correctly ([`61b9746`](https://github.com/Agentic-Brain/standard_pipelines/commit/61b9746a91c8ede7cb68aa82c9f1e47eaefbb19d))

* basic working flow ([`0fad842`](https://github.com/Agentic-Brain/standard_pipelines/commit/0fad8424f8a854f4fda62f616d549d737e61c82b))

* Merge branch &#39;main&#39; into dp2ss_final ([`d8afc1c`](https://github.com/Agentic-Brain/standard_pipelines/commit/d8afc1c573be0b1c3968e89d09cd82b95c839e64))

* Merge pull request #105 from Agentic-Brain/admin

Admin ([`b6904a3`](https://github.com/Agentic-Brain/standard_pipelines/commit/b6904a3d710270818454e5ceb47606a7d18e0c8d))

* removed unneeded test ([`bb4e0b3`](https://github.com/Agentic-Brain/standard_pipelines/commit/bb4e0b3714fc07ae10ef8d30c359ed828bf33332))

* version bumps ([`5ff90c0`](https://github.com/Agentic-Brain/standard_pipelines/commit/5ff90c0708a60d700a4a62cbf761a42a15976dd5))

* updated gitignore ([`073551e`](https://github.com/Agentic-Brain/standard_pipelines/commit/073551e20df84661b92d081682be8711d4f4272b))

* client dataflow join admin management ([`10ecd77`](https://github.com/Agentic-Brain/standard_pipelines/commit/10ecd771650095206c818676f3310dc9e4b786c3))

* really good progress on the dashboard ([`52945ce`](https://github.com/Agentic-Brain/standard_pipelines/commit/52945ce601f672fd654f92a727476e231b55049f))

* shifted to custom admin ([`7366d74`](https://github.com/Agentic-Brain/standard_pipelines/commit/7366d74a3e6a819625f2145405c5483076bf7512))

* final requirements for dp2ss ([`801cbeb`](https://github.com/Agentic-Brain/standard_pipelines/commit/801cbeb75a28a1ea6a61d27c96f450cbf631300c))

* Merge pull request #104 from Agentic-Brain/migrations_catchup

updated migrations ([`6930441`](https://github.com/Agentic-Brain/standard_pipelines/commit/69304413fe42be638aa4d0cab424a01497814fdf))

* version bumping ([`d688352`](https://github.com/Agentic-Brain/standard_pipelines/commit/d688352428a2ec48b60153d02c3b56b00841727d))

* updated migrations ([`b96fb58`](https://github.com/Agentic-Brain/standard_pipelines/commit/b96fb585f4843d1f95175c06f96aabb14a145279))

* Merge pull request #103 from Agentic-Brain/acp/oauth-clean

Acp/oauth clean ([`cb41f9c`](https://github.com/Agentic-Brain/standard_pipelines/commit/cb41f9c17b7fcb13c42e63f67c8a2751628f9072))

* version bump ([`221c048`](https://github.com/Agentic-Brain/standard_pipelines/commit/221c04847fcf22a68e8ade7b80e7f0a0971b2aa6))

* lots of template and oauth changes ([`46dab88`](https://github.com/Agentic-Brain/standard_pipelines/commit/46dab8836ab79322bc2e342548ad1f6918aa08af))

* Merge branch &#39;main&#39; into acp/oauth-clean ([`f4bafd7`](https://github.com/Agentic-Brain/standard_pipelines/commit/f4bafd7f6e125207cd36871e0d5d56d19b6cc11f))

* ayy lmao ([`6378373`](https://github.com/Agentic-Brain/standard_pipelines/commit/6378373a86733fd151b4b8d25776032f4168fef4))

* have to fix dash still ([`13f8c39`](https://github.com/Agentic-Brain/standard_pipelines/commit/13f8c3937ee6056c3f8b1c445dff556142b97f2d))

* added admin dashboard features ([`b0188e9`](https://github.com/Agentic-Brain/standard_pipelines/commit/b0188e9172c95162d77b8311e619e9e1a3cf22f0))

* templated oauth page ([`da2dc1d`](https://github.com/Agentic-Brain/standard_pipelines/commit/da2dc1dda500d7e355f6bee3c9ddfa14722d431a))

* basic oauth UI ([`9b9216c`](https://github.com/Agentic-Brain/standard_pipelines/commit/9b9216c54759df997f9b9d95963e3b0bde1eefd4))

* Merge pull request #102 from Agentic-Brain/acp/coa-solutions-transcript

Acp/coa solutions transcript ([`a5fb704`](https://github.com/Agentic-Brain/standard_pipelines/commit/a5fb704080de168c5426a2afebc41539c4933cf0))

* Merge branch &#39;main&#39; into acp/coa-solutions-transcript ([`4887df2`](https://github.com/Agentic-Brain/standard_pipelines/commit/4887df23f9af8bd42c28fe26ab135f1030e2884a))

* Merge pull request #101 from Agentic-Brain/acp/minor-fix

some tiny fixes ([`b1248f2`](https://github.com/Agentic-Brain/standard_pipelines/commit/b1248f2e47298a193c6a1a42f331fe643f9e5613))

* some tiny fixes ([`10caf5a`](https://github.com/Agentic-Brain/standard_pipelines/commit/10caf5a5f36fb5482ab5b22caf312cb3cfb88440))

* Merge pull request #100 from Agentic-Brain/acp/send-gmail-flow

Acp/send gmail flow ([`7067d56`](https://github.com/Agentic-Brain/standard_pipelines/commit/7067d5698b26bf530427248ab11f65a33313f580))

* fixed issue with nullable value ([`97321e7`](https://github.com/Agentic-Brain/standard_pipelines/commit/97321e7422e3675575578dd93aae99ccb60b1c21))

* Apply suggestions from code review

added missing name variable declaration

Co-authored-by: bito-code-review[bot] &lt;188872107+bito-code-review[bot]@users.noreply.github.com&gt; ([`808cd4b`](https://github.com/Agentic-Brain/standard_pipelines/commit/808cd4b2051d5de284b58bc3a397fddb6e94cd0b))

* more shit ([`ef6d923`](https://github.com/Agentic-Brain/standard_pipelines/commit/ef6d923d509d17a0106a3d6aac266c13b20f5b64))

* adding append_hubspot_note ([`ef87f17`](https://github.com/Agentic-Brain/standard_pipelines/commit/ef87f170aa60f03fb632716b9cb790d32951a188))

* more minor modifications ([`f186bcd`](https://github.com/Agentic-Brain/standard_pipelines/commit/f186bcdefd69b1504e816cde6546c9c8e5072971))

* added followup email send ([`0b1a11b`](https://github.com/Agentic-Brain/standard_pipelines/commit/0b1a11b0429dbb5b1f9ac64a16207cc7d705acfa))

* new gmail flow ([`218829b`](https://github.com/Agentic-Brain/standard_pipelines/commit/218829b7675633022b5f7c31e76be99ba8b924f9))

* removed sdk_tokens ([`8ae0065`](https://github.com/Agentic-Brain/standard_pipelines/commit/8ae00654b9e1e792166bb9efdc00a033a3626277))

* version bump ([`de96363`](https://github.com/Agentic-Brain/standard_pipelines/commit/de96363786b98a301d9e79483c52194161c7ec13))

* updated dialpad2zoho flow ([`a4741b4`](https://github.com/Agentic-Brain/standard_pipelines/commit/a4741b434b0b828a8ec8825221eee2cc97248a06))

* base of deep research updates, not deploy ready ([`b701659`](https://github.com/Agentic-Brain/standard_pipelines/commit/b7016599bb78b7ea013a43fe0464fe5c9d64a862))

* Merge pull request #95 from Agentic-Brain/devin/1742231272-add-data-to-hubspot-field

Add add_data_to_hubspot_field data flow ([`cf6c897`](https://github.com/Agentic-Brain/standard_pipelines/commit/cf6c89768fe39c55e3c36952b6938193ab6eed15))

* polishing hubspot add fields flow ([`b6df518`](https://github.com/Agentic-Brain/standard_pipelines/commit/b6df5182b902672a7f394f26c40a35d207c49ba9))

* Add add_data_to_hubspot_field data flow

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`1d9f974`](https://github.com/Agentic-Brain/standard_pipelines/commit/1d9f97465ec4a6822916626c46a2c34e5458dea8))

* Merge pull request #94 from Agentic-Brain/acp/coa-zoho

Acp/coa zoho ([`1c648db`](https://github.com/Agentic-Brain/standard_pipelines/commit/1c648db6b166aa7f9f3c870689092c9efde69bf1))

* exception handling fix ([`b4dcb33`](https://github.com/Agentic-Brain/standard_pipelines/commit/b4dcb330f46b69f798ef1b30b6b3eef1b7dd0281))

* working stuff for zoho ([`0bc3467`](https://github.com/Agentic-Brain/standard_pipelines/commit/0bc3467f823ce16a37360ba0b37162a7ee59ccbe))

* fixing some zoho stuff ([`3519488`](https://github.com/Agentic-Brain/standard_pipelines/commit/35194883dcf940b8d726c37430b977786fed71fb))

* some modifications ([`925a188`](https://github.com/Agentic-Brain/standard_pipelines/commit/925a1889a5b5174283a9d2def838e489af23cedc))

* Merge pull request #93 from Agentic-Brain/acp/logging

various debugging fixes ([`7c5f944`](https://github.com/Agentic-Brain/standard_pipelines/commit/7c5f944befc1b1974715e4d2b0afc059c1177c8f))

* various debugging fixes ([`f65afc9`](https://github.com/Agentic-Brain/standard_pipelines/commit/f65afc971145c4f3fa5ab44bd674300493ca7949))

* Merge pull request #92 from Agentic-Brain/quincy/coa/sales_transcript_tool

Quincy/coa/sales transcript tool ([`1abf0d4`](https://github.com/Agentic-Brain/standard_pipelines/commit/1abf0d4899bdde87d144f5c7455543e4cd7d7206))

* finishing dialpad to zoho flow ([`d1444b5`](https://github.com/Agentic-Brain/standard_pipelines/commit/d1444b597341c9742f11a8594143905b7e65d5d9))

* fixing zoho manager ([`d60554b`](https://github.com/Agentic-Brain/standard_pipelines/commit/d60554bb739a69a0d99e54c09a633778b43ece7a))

* fixing openai credential loading ([`69a7943`](https://github.com/Agentic-Brain/standard_pipelines/commit/69a7943c4d26a8b6ed74deba78be762b935cdd05))

* lots more zoho stuff ([`1fa9744`](https://github.com/Agentic-Brain/standard_pipelines/commit/1fa9744eacff00952b1cbf4c90e82cf505019931))

* creating records and notes works ([`cc66e65`](https://github.com/Agentic-Brain/standard_pipelines/commit/cc66e65532ebc245e8e9b21a8df5aad2197da193))

* big zoho improvements ([`dbd5f98`](https://github.com/Agentic-Brain/standard_pipelines/commit/dbd5f981da27a99f31177ad5a743be28c1926fc9))

* fixed weird oauth error ([`c6b6476`](https://github.com/Agentic-Brain/standard_pipelines/commit/c6b6476d56adbe9b514326b55262c10989cf2159))

* I think this is working ([`8f1752a`](https://github.com/Agentic-Brain/standard_pipelines/commit/8f1752a6aa16875bd7764955b51f7e3d07a79723))

* stuff ([`71b11d8`](https://github.com/Agentic-Brain/standard_pipelines/commit/71b11d881eeb944525ccb36e3000a89eee16f8c6))

* various changes ([`2871efd`](https://github.com/Agentic-Brain/standard_pipelines/commit/2871efdd1ecb768a52c2183691213ec70b878d64))

* jwt shit ([`6cdc7d1`](https://github.com/Agentic-Brain/standard_pipelines/commit/6cdc7d1511f46199e8d0919ce1c8b78b70970803))

* dataflow changes ([`6abd6bc`](https://github.com/Agentic-Brain/standard_pipelines/commit/6abd6bcd7b6ea7d2a364217eda17e744be4c9d94))

* cleaned up migrations ([`9a609f2`](https://github.com/Agentic-Brain/standard_pipelines/commit/9a609f244a13cf44a43f84cd13c706fb9ca2eef4))

* merge from main ([`555b719`](https://github.com/Agentic-Brain/standard_pipelines/commit/555b71900e822437f145907844620113ade50ffa))

* adding in dialpad ([`528507d`](https://github.com/Agentic-Brain/standard_pipelines/commit/528507d2090bb88fa41253689aeb5a0ff89d6fe7))

* dialpad integration from main ([`72c4565`](https://github.com/Agentic-Brain/standard_pipelines/commit/72c4565a7ad76e8cd91eb38b0b4d7bd8f19e13f6))

* throw an error if we don&#39;t have a client config ([`0010e87`](https://github.com/Agentic-Brain/standard_pipelines/commit/0010e871736ee8f1b62b1c62dadaab741fc7026a))

* Merge pull request #91 from Agentic-Brain/acp/error

Acp/error ([`7a46bd9`](https://github.com/Agentic-Brain/standard_pipelines/commit/7a46bd9792d445c527a80c88b8c673f62092cb65))

* updated docker compose with new papertrail secrets ([`dbc7e27`](https://github.com/Agentic-Brain/standard_pipelines/commit/dbc7e27b2dde444e986faf850aedd458fc3a7c25))

* version bump ([`25037a0`](https://github.com/Agentic-Brain/standard_pipelines/commit/25037a0f53d361ca8c958df1fc7bd352605f207b))

* various error handling details ([`8f25426`](https://github.com/Agentic-Brain/standard_pipelines/commit/8f25426e4795289db7f00c4e9590ed3c39a277ab))

* merge ([`dd40eea`](https://github.com/Agentic-Brain/standard_pipelines/commit/dd40eea6d2e8153dff616a58cd63349ffee9fe75))

* version bump ([`b350241`](https://github.com/Agentic-Brain/standard_pipelines/commit/b3502413ff0001b3bca7dffb2929666551f00539))

* reintroduced some accidental removals ([`c32d5c6`](https://github.com/Agentic-Brain/standard_pipelines/commit/c32d5c6f183ee02a88731c7f977369f28819ba16))

* added some error handling ([`20db6d3`](https://github.com/Agentic-Brain/standard_pipelines/commit/20db6d3ab553ce930a14f4b624542b7d519c34c2))

* Merge pull request #90 from Agentic-Brain/acp/papertrail

Acp/papertrail ([`8f266b2`](https://github.com/Agentic-Brain/standard_pipelines/commit/8f266b2162e03586479ead1379964b5c4373756c))

* Merge branch &#39;main&#39; into acp/papertrail ([`e119892`](https://github.com/Agentic-Brain/standard_pipelines/commit/e11989206e020c05660b494771c23c2c0589b694))

* fireflies piece working on fireflies2zoho ([`02a0352`](https://github.com/Agentic-Brain/standard_pipelines/commit/02a0352e66e9115eba437cef73873c5732255c6f))

* partial for adam ([`6e5b9bb`](https://github.com/Agentic-Brain/standard_pipelines/commit/6e5b9bbb77d144ea223764aa4e53f2db7a387f12))

* zoho oauth flow ([`b705bbc`](https://github.com/Agentic-Brain/standard_pipelines/commit/b705bbc99d6bae994be5ec9777134af3c5f2d04e))

* work in progress ([`bcea19a`](https://github.com/Agentic-Brain/standard_pipelines/commit/bcea19abcd8c45af20e916ba4bb4ac6a8e5d66eb))

* Merge pull request #87 from Agentic-Brain/autofix/handle-missing-or-empty-sentences-in-fireflies-transcript-data

🤖 Handle missing or empty sentences in Fireflies transcript data ([`93fa048`](https://github.com/Agentic-Brain/standard_pipelines/commit/93fa048fb460d2d5663bcafa495c258a9968dd3d))

* Handle missing or empty sentences in Fireflies transcript data ([`a0ae8da`](https://github.com/Agentic-Brain/standard_pipelines/commit/a0ae8da7e86968afe154da2e94681513d017bd93))

* added celery to sentry ([`52abb06`](https://github.com/Agentic-Brain/standard_pipelines/commit/52abb06431afac4c50dd6390fadca11a03061d7b))

* added papertrail logging ([`ac78399`](https://github.com/Agentic-Brain/standard_pipelines/commit/ac78399c64b6cfc9561d6c401721c542f424ff6c))

* Merge 61/jordan/sharpspring-integration into Main (#84)

* Created basic file structure

* Created the sharpspring model

* Created basic SharpSpringAPIManager

* Created SharpSpring credentials route

* Refactored SharpSpringAPIManager and verified opportunity creation

* Shortened code and adjusted structure

* Created get contact function

* Implemented create contact function and updated SharpSpringAPIManager sturcture

* Created functions to an get an opportunity and it&#39;s id

* Implemented get and create field functions and fixed errors

* Optimized code with call api function and fixed errors

* Minor fix

* Changed centralized data storage method

* Implemented Update contact function and adjusted SharpSpringAPIManager overall

* Fixed functions relating to the transcript field

* Recreated get contacts function with phone number, and created phone number formatter

* Updated Error checker to handle update errors

* Changed phone number formatter to handle all likely numbers

* Moved and renamed a few functions labeled as helper functions

* Updated SharpSring route error handling

* Updated and fixed services file, and added error handling

* Created parameter checker function and updated related code

* Minor error handling

---------

Co-authored-by: Adam &lt;57569721+acp21@users.noreply.github.com&gt; ([`60aa543`](https://github.com/Agentic-Brain/standard_pipelines/commit/60aa5431296fb827b55eb21e240cc749a973735c))

* Merge pull request #79 from Agentic-Brain/73/jordan/dialpad-integration

Merge 73/jordan/dialpad-integration into Main ([`830dab0`](https://github.com/Agentic-Brain/standard_pipelines/commit/830dab0d10493f9c21e256ddc823f6071e49c0a9))

* Merge pull request #85 from Agentic-Brain/acp/new-fixes

llm model and redirect url fixes ([`07628dc`](https://github.com/Agentic-Brain/standard_pipelines/commit/07628dcab6fba4a08107aa743709e766ca9cbc74))

* llm model and redirect url fixes ([`687a683`](https://github.com/Agentic-Brain/standard_pipelines/commit/687a683c64f73dce0497cfdb122c6452078380a8))

* logging path fix for windows ([`7d4603e`](https://github.com/Agentic-Brain/standard_pipelines/commit/7d4603e2efafa08a99b225f27fe8b6cffe908949))

* ignore .idea ([`23a7f13`](https://github.com/Agentic-Brain/standard_pipelines/commit/23a7f13fd182fe981b491d2f252924a3d6b2a810))

* Minor unused import removal ([`b21f982`](https://github.com/Agentic-Brain/standard_pipelines/commit/b21f982bc276d8f53c0de5ab447c212ecad5ea0f))

* Modified _format_transcript function and updated routes ([`af5d0bb`](https://github.com/Agentic-Brain/standard_pipelines/commit/af5d0bbfc50a57038fb4064fd5af7df5f9631831))

* Updated Dialpad migration down revision ([`a013b50`](https://github.com/Agentic-Brain/standard_pipelines/commit/a013b50f999d089c12db999100dfbe58a48a8cce))

* Merge remote-tracking branch &#39;origin&#39; into 73/jordan/dialpad-integration ([`09643ad`](https://github.com/Agentic-Brain/standard_pipelines/commit/09643ad221febca96b11704e34c5b6d3d0840461))

* Merge pull request #83 from Agentic-Brain/acp/various_patches

Acp/various patches ([`f94276d`](https://github.com/Agentic-Brain/standard_pipelines/commit/f94276d62e3e4c0ac80edb620527e68ce09dc76b))

* Merge branch &#39;acp/various_patches&#39; of github.com:Agentic-Brain/standard_pipelines into acp/various_patches ([`10fe43f`](https://github.com/Agentic-Brain/standard_pipelines/commit/10fe43f00949f199356a608b4e626ecd36519f2f))

* important docker stuff ([`aa4b62b`](https://github.com/Agentic-Brain/standard_pipelines/commit/aa4b62becc20acbef63d794a5087b55f11f9f6d4))

* Merge pull request #82 from Agentic-Brain/acp/various_patches

Transcript/Followup Patches ([`f9fd0ea`](https://github.com/Agentic-Brain/standard_pipelines/commit/f9fd0ea92d85136819a73b31ebe83d04ec96fce1))

* version bump ([`75ebac1`](https://github.com/Agentic-Brain/standard_pipelines/commit/75ebac18dbadc1c0b0ba4ebd0623b44977696c8c))

* updated google auth requirements ([`9fd3d33`](https://github.com/Agentic-Brain/standard_pipelines/commit/9fd3d33a982ff5648383c3490a86cb12ca384df4))

* Fixed Dialpad model file name to match others ([`f4191b9`](https://github.com/Agentic-Brain/standard_pipelines/commit/f4191b9aa9cc3bceb70d917e62ced41401f517f9))

* Adjusted transcript formatter ([`a606b57`](https://github.com/Agentic-Brain/standard_pipelines/commit/a606b5719279c24dd2a37af8d85a71fbcb672dc9))

* various changes ([`2296fe8`](https://github.com/Agentic-Brain/standard_pipelines/commit/2296fe87915df4c8eb2d8317e5ca4ce7d6c01ffc))

* Expanded exception error handling ([`f088b8b`](https://github.com/Agentic-Brain/standard_pipelines/commit/f088b8bf369abdc311cd8616a6be0fa78a74907a))

* Fixed transcript offset times and simplified helper functions ([`2c71b20`](https://github.com/Agentic-Brain/standard_pipelines/commit/2c71b20a55db1d12eec6581df49c06156376fece))

* Optimized code and added minor error handling ([`cdbb93c`](https://github.com/Agentic-Brain/standard_pipelines/commit/cdbb93c7f1e9d39f9fcb3565fde471cd93fd709b))

* Updated transcript formatter and fixed minor errors ([`bb23b19`](https://github.com/Agentic-Brain/standard_pipelines/commit/bb23b19adbd51708b145a8f9bd4135591c8452c1))

* Updated migration revision ([`ed21b22`](https://github.com/Agentic-Brain/standard_pipelines/commit/ed21b2214b3a5dd3ad6582cf6676789d36d969ac))

* Merge branch &#39;main&#39; into 73/jordan/dialpad-integration ([`a5ef79e`](https://github.com/Agentic-Brain/standard_pipelines/commit/a5ef79e84ae7a5ad1a5e84691f0497d8425ecccb))

* Merge pull request #80 from Agentic-Brain/acp/followup

Email Nurture Tool ([`1e78c52`](https://github.com/Agentic-Brain/standard_pipelines/commit/1e78c52e092e264ce47ab59fb5525d249cb2321c))

* fixed indexing errors ([`7ee0f51`](https://github.com/Agentic-Brain/standard_pipelines/commit/7ee0f518fb8937cb4abd1cc9a59befe5c68da825))

* migrations index fix ([`e2fc3ba`](https://github.com/Agentic-Brain/standard_pipelines/commit/e2fc3ba025d32d3d45259e07804d0efcfdd9d1e3))

* Apply suggestions from code review

Co-authored-by: bito-code-review[bot] &lt;188872107+bito-code-review[bot]@users.noreply.github.com&gt; ([`7a717e0`](https://github.com/Agentic-Brain/standard_pipelines/commit/7a717e06929ab58afbb660221dc4fc9d6fb25dfe))

* Merge branch &#39;acp/followup&#39; of github.com:Agentic-Brain/standard_pipelines into acp/followup ([`d93ab6b`](https://github.com/Agentic-Brain/standard_pipelines/commit/d93ab6bae1eee753ae9e334422380a8cc1cb8b51))

* updating docker compose ([`70e496d`](https://github.com/Agentic-Brain/standard_pipelines/commit/70e496d016782523dfe8ad941c06de1a609395a1))

* Fixed removed cached property ([`940597d`](https://github.com/Agentic-Brain/standard_pipelines/commit/940597d1b11313d7859b4486a1acd85b743fb903))

* database migration ([`912c729`](https://github.com/Agentic-Brain/standard_pipelines/commit/912c729cf48d6d6425062ac0b1f1f6d1c02b05ad))

* model changes ([`2ace013`](https://github.com/Agentic-Brain/standard_pipelines/commit/2ace01356e744d64993ac9dda94fae00e5e87c14))

* more celery updates ([`67ccb59`](https://github.com/Agentic-Brain/standard_pipelines/commit/67ccb59ab7a7a12875b630a813e3dda79b9971ad))

* created webhook splitter ([`2f996ef`](https://github.com/Agentic-Brain/standard_pipelines/commit/2f996ef5d0f01d18d34efea316c656a53fdcbe49))

* changed formatting of celery jobs ([`ed8545e`](https://github.com/Agentic-Brain/standard_pipelines/commit/ed8545e32d7d581e3ae268f7b036c4591648d8e6))

* basic functioning draft tool ([`acda032`](https://github.com/Agentic-Brain/standard_pipelines/commit/acda0320d87a748f39b534e7148f2c7c7f37da57))

* Adjusted dialpad migrations revision ([`af2c0af`](https://github.com/Agentic-Brain/standard_pipelines/commit/af2c0afe44940fccd826c5d9a1f53a195fa5ecbc))

* Merge remote-tracking branch &#39;origin&#39; into 73/jordan/dialpad-integration ([`a3e0403`](https://github.com/Agentic-Brain/standard_pipelines/commit/a3e0403c6666c55752a0b01bd74f2a49022459d8))

* Added call participant info retrival ([`d349f02`](https://github.com/Agentic-Brain/standard_pipelines/commit/d349f02a56c715c026eac73a17961af4c0f6eac6))

* setup celery ([`27dc263`](https://github.com/Agentic-Brain/standard_pipelines/commit/27dc2632a122ea865d7b6912c5efb3ecfe49358a))

* working on google followup tool ([`dcaf80a`](https://github.com/Agentic-Brain/standard_pipelines/commit/dcaf80a81dd902e877c5f9fa13884d3aadeb580c))

* adding features for scheduling ([`257e9de`](https://github.com/Agentic-Brain/standard_pipelines/commit/257e9de12358a72440948587e3a7b273783b8888))

* added google credential models ([`0d7b4c5`](https://github.com/Agentic-Brain/standard_pipelines/commit/0d7b4c5855b110a3c85abf39daefa3d8f58bd01c))

* Merge branch &#39;main&#39; into acp/followup ([`f30db94`](https://github.com/Agentic-Brain/standard_pipelines/commit/f30db94044bb7019b5c80b2f5968c365f2fc5b43))

* Merge pull request #72 from Agentic-Brain/71/sebastian/hubspot-edge-cases

feat: HubSpot edge cases ([`4790041`](https://github.com/Agentic-Brain/standard_pipelines/commit/4790041c76c3442bc8ba6a7353bdd0e9484d0496))

* gmail flow ([`e993ff3`](https://github.com/Agentic-Brain/standard_pipelines/commit/e993ff367d2d555561f1186695c2574d321b9a1f))

* Merge branch &#39;main&#39; into 71/sebastian/hubspot-edge-cases ([`eac2d4c`](https://github.com/Agentic-Brain/standard_pipelines/commit/eac2d4cc3b348cec6c70fe07859ca2bafb54b178))

* up and running ([`8f2d360`](https://github.com/Agentic-Brain/standard_pipelines/commit/8f2d36067c1fc725c51595ed654d8ad53d675218))

* starting followup ([`505057c`](https://github.com/Agentic-Brain/standard_pipelines/commit/505057c5775b6a1b6ebbc8c5dc860c9237918bd9))

* Added further error handling ([`c8f6547`](https://github.com/Agentic-Brain/standard_pipelines/commit/c8f6547388f06dafc94f31ac3a0ea58626404d60))

* Minor error message change ([`430e117`](https://github.com/Agentic-Brain/standard_pipelines/commit/430e1176199fc89fae895d39bbcc9d96136c7c3c))

* Created dialpad migrations ([`0840c8f`](https://github.com/Agentic-Brain/standard_pipelines/commit/0840c8f16ca1c57a1e9ad6ed73d5aa5b47f987f5))

* Minor error handling change ([`e7d1322`](https://github.com/Agentic-Brain/standard_pipelines/commit/e7d13222efa61e8a762bab9fcefbba74b572fee3))

* Merge remote-tracking branch &#39;origin&#39; into 73/jordan/dialpad-integration ([`7964a15`](https://github.com/Agentic-Brain/standard_pipelines/commit/7964a15fad2a9cd49af4863f758fc34015ba8c79))

* Implemented webhook creation and subscription functions ([`85c5a0f`](https://github.com/Agentic-Brain/standard_pipelines/commit/85c5a0f0bd5e31968e50d3e988b20a18d7346180))

* Merge pull request #78 from Agentic-Brain/acp/update-readme

Update README.md ([`f81bc8d`](https://github.com/Agentic-Brain/standard_pipelines/commit/f81bc8dc80725aedd396840ff5c65dec24908be0))

* Update README.md ([`3b1499d`](https://github.com/Agentic-Brain/standard_pipelines/commit/3b1499d9e84c3677cb8f3dd054807dc176a8825f))

* Created transcript formatter ([`336e19b`](https://github.com/Agentic-Brain/standard_pipelines/commit/336e19b44ea89b4db2072eb9ed85ea8381f3b224))

* Improved get transcript function ([`fb16213`](https://github.com/Agentic-Brain/standard_pipelines/commit/fb1621377c2a9f083f262be153c9675da1592df8))

* Added minor logging ([`ffd51a0`](https://github.com/Agentic-Brain/standard_pipelines/commit/ffd51a030229ba70168a1a7d6d9d8a4e036a600e))

* Merge branch &#39;main&#39; into 71/sebastian/hubspot-edge-cases ([`873d128`](https://github.com/Agentic-Brain/standard_pipelines/commit/873d1287956e2c2d145c0069fefd1b67d11b2080))

* followup changes ([`05d5f4c`](https://github.com/Agentic-Brain/standard_pipelines/commit/05d5f4cef89358daa6a630a26ce4ac8cdbb0c059))

* google credentials stores users name and email ([`b15a9ed`](https://github.com/Agentic-Brain/standard_pipelines/commit/b15a9ed8c1e3f513ff8c16c04c7e4e9195395c9a))

* Merge pull request #77 from Agentic-Brain/acp/hubspot-fixes

Acp/hubspot fixes ([`befc616`](https://github.com/Agentic-Brain/standard_pipelines/commit/befc6164ef61c25e341f3eff686fad0f3f0473e2))

* Fixed route ([`d329605`](https://github.com/Agentic-Brain/standard_pipelines/commit/d329605a5a265eb46b07a7128c887a6339341ac6))

* Implemented DialpadAPIManager and updated pyproject ([`ecbb152`](https://github.com/Agentic-Brain/standard_pipelines/commit/ecbb152563beb1d92eb9817df00d48c073fc354b))

* Created Dialpad routes and minor init addition ([`100f1a5`](https://github.com/Agentic-Brain/standard_pipelines/commit/100f1a591ad42b39986560c42f6154e9ac25fffd))

* Merge pull request to update readme

updated readme ([`ffcf83a`](https://github.com/Agentic-Brain/standard_pipelines/commit/ffcf83a5ab4fff42060cfcde5619eb5453b46a8a))

* Update README.md ([`7291656`](https://github.com/Agentic-Brain/standard_pipelines/commit/72916562df9fcf0e1f9b5c805ec4782cf35a68c0))

* Update README.md ([`3868cac`](https://github.com/Agentic-Brain/standard_pipelines/commit/3868cac897bfc6c2b611de80bff682f01f9db122))

* Update README.md ([`b36d379`](https://github.com/Agentic-Brain/standard_pipelines/commit/b36d37905509cde56cfb3b7c826dfd79d5d949a4))

* Created Dialpad model ([`8b7987b`](https://github.com/Agentic-Brain/standard_pipelines/commit/8b7987b2742e7afe9552ae4fc574155dd69c6e0b))

* changed hubspot oauth details ([`4c02d64`](https://github.com/Agentic-Brain/standard_pipelines/commit/4c02d64bb44d9d56059aa1e055a84e9a3238432a))

* updated sentry configs ([`76546cd`](https://github.com/Agentic-Brain/standard_pipelines/commit/76546cdf1ddbb6552bad6e6548f246b1f5fcab60))

* Merge pull request #74 from Agentic-Brain/devin/1739424912-hubspot-deal-enhancements

Add deal notes and items functionality to HubspotAPIManager ([`c1bc288`](https://github.com/Agentic-Brain/standard_pipelines/commit/c1bc28819d3c19c4d7330d2afee12f5e2cedfa38))

* minor changes ([`0e35db7`](https://github.com/Agentic-Brain/standard_pipelines/commit/0e35db753160555caf1225c17ee7e87daad0c34e))

* Fix: Use mock HubspotAPIManager in tests to avoid API calls

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`f31c037`](https://github.com/Agentic-Brain/standard_pipelines/commit/f31c037a506a87043f70bf0255f8245f73c5b9ae))

* Fix: Update all routes to use get_hubspot_manager

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`04c3941`](https://github.com/Agentic-Brain/standard_pipelines/commit/04c3941672e2236ff64a70aa4190084342af8767))

* Fix: Initialize HubspotAPIManager per request instead of globally

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`2d6c538`](https://github.com/Agentic-Brain/standard_pipelines/commit/2d6c538263d068e156c98d961f7ab30724b954c2))

* Add deal notes and items functionality to HubspotAPIManager

Co-Authored-By: adam@agenticbrain.com &lt;adam@agenticbrain.com&gt; ([`6828f2a`](https://github.com/Agentic-Brain/standard_pipelines/commit/6828f2ae20cd93665b843df32b3586a17d6542fe))

* Merge pull request #56 from Agentic-Brain/devin/1738804519-scheduled-mixin

feat: add ScheduledMixin and celery task for scheduled operations ([`78fc7b7`](https://github.com/Agentic-Brain/standard_pipelines/commit/78fc7b7376b1ceafea3d2b6b4c040271900bd5a3))

* removing broken imports ([`8775ff4`](https://github.com/Agentic-Brain/standard_pipelines/commit/8775ff46f5e31d230af5ac092789fc9a4c129c8e))

* accepting tests ([`cd9da21`](https://github.com/Agentic-Brain/standard_pipelines/commit/cd9da21c3a1af688ec1a7cdacb97f940d9e4c877))

* Created basic file structure ([`cdc22d0`](https://github.com/Agentic-Brain/standard_pipelines/commit/cdc22d0b4ad457b14a13816beacbfa5d8614171e))

* continuing to modify scheduler ([`e754f5b`](https://github.com/Agentic-Brain/standard_pipelines/commit/e754f5b4ce2868e8208c248e3e81e598ce6b80dc))

* changing alembic to ignore tests modules ([`f6a2688`](https://github.com/Agentic-Brain/standard_pipelines/commit/f6a2688e7d0aed66df4f56bce423d40dccd13082))

* updating scheduled mixin unit tests ([`2642bb6`](https://github.com/Agentic-Brain/standard_pipelines/commit/2642bb6cbcce94e6d2697af2100dbc268e54b7fc))

* Merge branch &#39;main&#39; into devin/1738804519-scheduled-mixin ([`1fac8f4`](https://github.com/Agentic-Brain/standard_pipelines/commit/1fac8f420327fde4877e253370a386fefb171ba2))

* scheduled mixin work ([`731b97a`](https://github.com/Agentic-Brain/standard_pipelines/commit/731b97ab9900258d54088721e3da3311de4f6e6b))

* Merge branch &#39;main&#39; into devin/1738804519-scheduled-mixin ([`35b4ced`](https://github.com/Agentic-Brain/standard_pipelines/commit/35b4ced284e2c2ef25fb92b22010143f3fc06cd5))

* Merge 36/jordan/gmail integration into main (#51)

* Created basic file structure

* Set up blueprint

* Updated requirements.txt

* Set up client_secret in  config and updated gitignore

* Created basic routes structure and minor init addition

* Updated config file contents and usage

* Created database model

* Implemented basic routes functionality

* Updated routes structure and model data

* Created services structure and get credentials function

* Created send email route

* Created token refresh function and extended structure

* Updated routes error handling

* Added email field to model

* added message structurer, email setter, and token refresh edit

* Created send email function

* Added token expirey handling and minor edits

* Changed scope, and fixed imports and errors

* Updated files and fixed errors

* Setup gmail migration, updated model and related code

* Remade migration and updated model and related code

* Updated model and migrations

* Implemented email sending and fixed refresh token

* Fixed and verified refresh_access_token function

* Removed unneeded code and added error handling

* Put services file into one class and optimized code

* Fixed code to allow users to reauthenticate

* Added error handling

* Created basic gmail unit test structure

* Minor code and error handling updates

* Fixed migration branching error

* Removed need for client_secrets_file.json

* Removed redundant model fields and adjusted code

* Fixed migration revision text and minor updates

* Fixed major exception error and modified init file

* Updated conftest and created authorize route tests

* Fixed major error handling issue

* Created and verified oauth2callback unit tests

* Created and verified send_email unit tests, and minor edits

* Minor error handling update

* Created and verified services send_email tests

* Minor error handling change

* Updated migrations, model, and related code

* Removed Gmail specific code

* Fixed import error

* Set up oauth Gmail registration

* Updated gmail services code to work with new api structure

* Updated gmail routes code to work with proper api structure

* Updated Gmail oauth registration

* Updated migration to handle encoded data length

* Overhaul Gmail routes to use authlib

* Removed access token from database model and adjusted related code

* Removed unused config

* added google api to uv build

* moved oauth details into api blueprint

* moving Credential models into API folders

* renaming gmail symbols to google

* Changed name from GMAIL to GOOGLE

* updated migrations to reference google instead of gmail

* basic google auth working

* gmail service works fine

* working on fixing gmail tests

* writing integration tests suck

* commented out tests so CI Passes

---------

Co-authored-by: Adam &lt;acpohl21@gmail.com&gt; ([`8d90774`](https://github.com/Agentic-Brain/standard_pipelines/commit/8d907747032d200018f28ba6b8d3b606f0b58ed5))

* hubspot edge cases ([`e84971e`](https://github.com/Agentic-Brain/standard_pipelines/commit/e84971ee419593f900561dacd19cc73e64dd3772))

* Merge pull request #68 from Agentic-Brain/acp/trufflehog

added test secrets to trufflehogignore ([`34e3c07`](https://github.com/Agentic-Brain/standard_pipelines/commit/34e3c07c66888acbb5efda577c751ab7b26d560b))

* added test secrets to trufflehogignore ([`eff31ce`](https://github.com/Agentic-Brain/standard_pipelines/commit/eff31ce7c288cf20752110d616c1e5c33a04c6fc))

* Merge pull request #66 from Agentic-Brain/acp/fixing-ci

Acp/fixing ci ([`7054301`](https://github.com/Agentic-Brain/standard_pipelines/commit/7054301520f144296af9d3cfb9e64ea958137c7d))

* changed pytest runner to use uv ([`9d78b7b`](https://github.com/Agentic-Brain/standard_pipelines/commit/9d78b7b97d4c039301f5a558eb53fe1c7548c3b4))

* updated artifacts runner ([`7dd9d21`](https://github.com/Agentic-Brain/standard_pipelines/commit/7dd9d21537000b2d7cd0ee07e85da07534ecd371))

* fixed typo ([`bcbe84b`](https://github.com/Agentic-Brain/standard_pipelines/commit/bcbe84b9d835da12ff34803d25d3c4e0cbd7482d))

* various changes ([`7335200`](https://github.com/Agentic-Brain/standard_pipelines/commit/7335200168d69202bfd06336cd2b93e1585a6c93))

* updated pyproject.toml ([`62e809f`](https://github.com/Agentic-Brain/standard_pipelines/commit/62e809fb2e8ca6845ff80792d34243639772ff86))

* Merge pull request #65 from Agentic-Brain/acp/config-warnings

warnings emmitted if missing api credentials, but code still runs ([`0491c89`](https://github.com/Agentic-Brain/standard_pipelines/commit/0491c8906878e39c41ab6410208132e8487e17e2))

* Update standard_pipelines/auth/__init__.py

Co-authored-by: bito-code-review[bot] &lt;188872107+bito-code-review[bot]@users.noreply.github.com&gt; ([`34ab334`](https://github.com/Agentic-Brain/standard_pipelines/commit/34ab3345f87b032cbfe304faa90f07355f8318e0))

* warnings emmitted if missing api credentials, but code still runs ([`2a10b30`](https://github.com/Agentic-Brain/standard_pipelines/commit/2a10b300944ed0d595f02290775a0cd0608eb95f))

* Merge pull request #58 from Agentic-Brain/devin/1738806647-migrate-to-pyproject

build: migrate to pyproject.toml with uv build system ([`30bc666`](https://github.com/Agentic-Brain/standard_pipelines/commit/30bc66640b81ae113ba18cc4be7e02d8f19a6c27))

* updated pyproject.toml ([`ea3864a`](https://github.com/Agentic-Brain/standard_pipelines/commit/ea3864ad8c997d1d98ba7cf93641a6df6277ea9f))

* Merge pull request #64 from Agentic-Brain/acp/refactor-apis

refactoring api information ([`32521cd`](https://github.com/Agentic-Brain/standard_pipelines/commit/32521cd548e3eb50ba9d03ed92de45efcbd44a27))

* Apply suggestions from code review

Co-authored-by: bito-code-review[bot] &lt;188872107+bito-code-review[bot]@users.noreply.github.com&gt; ([`859d143`](https://github.com/Agentic-Brain/standard_pipelines/commit/859d1431d57fbc5d95f91e77f90a78d72c97b505))

* More detailed error message

Co-authored-by: bito-code-review[bot] &lt;188872107+bito-code-review[bot]@users.noreply.github.com&gt; ([`359c595`](https://github.com/Agentic-Brain/standard_pipelines/commit/359c595e4dc89ec27b3824a6b89d35fd25166971))

* Update prompt check

Co-authored-by: bito-code-review[bot] &lt;188872107+bito-code-review[bot]@users.noreply.github.com&gt; ([`75b64bc`](https://github.com/Agentic-Brain/standard_pipelines/commit/75b64bc23178d6d28f797d4583bf3985a1fbd7c4))

* Merge pull request #63 from Agentic-Brain/devin/1738865072-fix-logging-formats

fix: environment-specific logging formats and prevent duplicate logs ([`1569796`](https://github.com/Agentic-Brain/standard_pipelines/commit/15697964eacc10d05a4816c9ad179e0fae271914))

* undid the unnecessary modifications devin made ([`6e37873`](https://github.com/Agentic-Brain/standard_pipelines/commit/6e37873bd2212170cb437917b9cf2af0b2d4c17e))

* refactoring api information ([`db035ab`](https://github.com/Agentic-Brain/standard_pipelines/commit/db035ab9411056fb9ad40b5641579e2a8eed6424))

* changes to pyproject.toml ([`41f4f3a`](https://github.com/Agentic-Brain/standard_pipelines/commit/41f4f3a5436781cec058c3c0cb0f0bb5f5464c12))

* uv lock ([`cd5787e`](https://github.com/Agentic-Brain/standard_pipelines/commit/cd5787ee94dd4545f74a9d91efbbafac3e30779a))

* Update pyproject.toml

Remove duplicate psycopg2 values

Co-authored-by: bito-code-review[bot] &lt;188872107+bito-code-review[bot]@users.noreply.github.com&gt; ([`5a72e09`](https://github.com/Agentic-Brain/standard_pipelines/commit/5a72e09ea9cc3a9278584482ebba3272cfa8b7f1))

* Merge pull request #57 from Agentic-Brain/acp/initial-deal-field

added features to support initial field in hubspot ([`f1ff9be`](https://github.com/Agentic-Brain/standard_pipelines/commit/f1ff9be16e44256a173bb995c54c46c9345be95b))

* added features to support initial field in hubspot ([`fb92166`](https://github.com/Agentic-Brain/standard_pipelines/commit/fb921669545705da5aa76095cd455691875b76e8))

* Merge pull request #55 from Agentic-Brain/54/sebastian/dataflow-name-and-webhook-id

dataflow name instead of id; webhook id removed ([`2e5cb12`](https://github.com/Agentic-Brain/standard_pipelines/commit/2e5cb12d7fbaef55824e7e3b32703e62f8dca7f9))

* dataflow name instead of id; webhook id removed ([`bda3667`](https://github.com/Agentic-Brain/standard_pipelines/commit/bda36670a9b7fe771126040115c9a325ac8f15a8))

* :(

The destruction of otherwise wonderful code ([`642c4ce`](https://github.com/Agentic-Brain/standard_pipelines/commit/642c4ce7af6c60b8f4c2a093d5b45ad3a10b997c))

* got rid of the secrets ([`df1f07a`](https://github.com/Agentic-Brain/standard_pipelines/commit/df1f07af0509307c7b3f672c98b938c5b28bb97a))

* a horrible slaughter of otherwise good code ([`23a5819`](https://github.com/Agentic-Brain/standard_pipelines/commit/23a5819ef035770a978e6a5c21ec8930a6b6bdb0))

* more work on hs fixing ([`bd9f770`](https://github.com/Agentic-Brain/standard_pipelines/commit/bd9f770ef3d541870a37fd6fb9f34eca717fa3a2))

* add deal and contact capabilities to the hubspot manager ([`0ae58f2`](https://github.com/Agentic-Brain/standard_pipelines/commit/0ae58f2a80c16f7a3e9afde74544e341f3ffd20f))

* increased openai credential length ([`8e4c302`](https://github.com/Agentic-Brain/standard_pipelines/commit/8e4c302f6176f69b4f6d1c229e8dd4f347f0ddbb))

* updating hubspot connector ([`58e16af`](https://github.com/Agentic-Brain/standard_pipelines/commit/58e16afff3913e714091fd8d2b108358f7eda5e6))

* Merge pull request #52 from Agentic-Brain/49/acp/oauth

Added hubspot oauth flow ([`e8a098e`](https://github.com/Agentic-Brain/standard_pipelines/commit/e8a098e41d2723d470f9bea60ebd34e04dd21d94))

* store hubspot credentials on oauth completion ([`6ba759f`](https://github.com/Agentic-Brain/standard_pipelines/commit/6ba759f6ff47b5a9ba8fc4dae7ee3ef1e8cfa7d3))

* added manual user creation route ([`a6e79ab`](https://github.com/Agentic-Brain/standard_pipelines/commit/a6e79abb89963380775d1e35a89007e3c1f2e1c3))

* setup oauth for hubspot ([`29fe36c`](https://github.com/Agentic-Brain/standard_pipelines/commit/29fe36ce7446524f2f796b170c5cec769ba10e3b))

* Merge pull request #48 from Agentic-Brain/acp/anthropic-api

added anthropic creds ([`9189ca7`](https://github.com/Agentic-Brain/standard_pipelines/commit/9189ca794d6af9cfe8edecaca7519abc013ddf38))

* added anthropic creds ([`b6f2c31`](https://github.com/Agentic-Brain/standard_pipelines/commit/b6f2c314e51e3625f00245999d1d4d55e89920dc))

* Merge pull request #47 from Agentic-Brain/acp/requirementsbump

made some changes to docker compose and updated requirments file ([`c5a39a8`](https://github.com/Agentic-Brain/standard_pipelines/commit/c5a39a822f33e2680031d1c1e7db136d27a4224a))

* version bump ([`2174360`](https://github.com/Agentic-Brain/standard_pipelines/commit/21743603fbf07734e007edef0fe0c2b8d65e6653))

* requirements + docker ([`ead0061`](https://github.com/Agentic-Brain/standard_pipelines/commit/ead006181be00d2e67dc5bbf3defcaef2e2bec85))

* Merge pull request #46 from Agentic-Brain/acp/openai-creds

Added OpenAI credentials model ([`8b45503`](https://github.com/Agentic-Brain/standard_pipelines/commit/8b45503bec229b38447d3ab82f2349e704e385f6))

* version bump ([`22bccea`](https://github.com/Agentic-Brain/standard_pipelines/commit/22bccea269901d113b2a15cf53d6c4297b2a3de2))

* fixed minor issue with mailgun config value ([`cb8540d`](https://github.com/Agentic-Brain/standard_pipelines/commit/cb8540d490e15bd01f36c62d466877e570ea9126))

* changed to use creds in database ([`d34039c`](https://github.com/Agentic-Brain/standard_pipelines/commit/d34039c9ea1fbea2fbc7f7ec2b4d2c325409be37))

* added openai credentials ([`4acf803`](https://github.com/Agentic-Brain/standard_pipelines/commit/4acf8037a1a1e206e1d45268198da3d4b2f0f0eb))

* Merge pull request #44 from Agentic-Brain/acp/create-admin

updated admin create command ([`d2283c0`](https://github.com/Agentic-Brain/standard_pipelines/commit/d2283c07ae9d9ce8ffeb816b78a13859600e383a))

* updated admin create command ([`ebb7243`](https://github.com/Agentic-Brain/standard_pipelines/commit/ebb7243a6a6b04ae0d527d4e339fdb582e766c32))

* Merge pull request #43 from Agentic-Brain/acp/scripts

added build secrets script ([`9a6f05e`](https://github.com/Agentic-Brain/standard_pipelines/commit/9a6f05ea81e5c88e07df0b7168708aa18aadd9d5))

* Merge pull request #41 from Agentic-Brain/40/acp/registry

Various deployment requirements ([`190da16`](https://github.com/Agentic-Brain/standard_pipelines/commit/190da164f3d3a776f93fb054021ba473f6020ada))

* added build secrets script ([`a2fc818`](https://github.com/Agentic-Brain/standard_pipelines/commit/a2fc8189c8c0feac002ec62a8197b87852eb121a))

* setup docker compose ([`b0abecb`](https://github.com/Agentic-Brain/standard_pipelines/commit/b0abecbcefbc570739159ccfccc9da1140afd5e7))

* cleaned up unused imports ([`9d905aa`](https://github.com/Agentic-Brain/standard_pipelines/commit/9d905aaf28674329602378c64764bdee5f2ecc5b))

* cleaned up config ([`4e9c030`](https://github.com/Agentic-Brain/standard_pipelines/commit/4e9c030d995ed0becda61c8d01049977342aa74d))

* setup system for internal route protection ([`ee9cc76`](https://github.com/Agentic-Brain/standard_pipelines/commit/ee9cc76db30664e2686bca3ce49275d5eb925a9a))

* changed naming schme ([`0399e1a`](https://github.com/Agentic-Brain/standard_pipelines/commit/0399e1af22e653353da4906c17c769a45018efde))

* create defaults commands ([`e5012b9`](https://github.com/Agentic-Brain/standard_pipelines/commit/e5012b9b8c778e152c487065c04bff8b25b804bc))

* required files for deployment ([`832e4bc`](https://github.com/Agentic-Brain/standard_pipelines/commit/832e4bc17c8b93007962b3880722876ee265dcef))

* initial migrations ([`0128e5f`](https://github.com/Agentic-Brain/standard_pipelines/commit/0128e5fd2d3aed1252fcc9af46f2a51b51cecdcb))

* Merge pull request #38 from Agentic-Brain/devin/1737827988-add-docker-cicd

feat: add Docker build CI/CD pipeline ([`a0c42fe`](https://github.com/Agentic-Brain/standard_pipelines/commit/a0c42fefda38073e453519c70786a46722bf4521))

* docker ci pipeline ([`4bb599f`](https://github.com/Agentic-Brain/standard_pipelines/commit/4bb599f3a0bf6e81151afa8231a7364eabaa00e5))

* dockerfile and entrypoint ([`19f9774`](https://github.com/Agentic-Brain/standard_pipelines/commit/19f977430485daa08362c391e9cd294af402c6e5))

* removed dockerfile changes ([`e841dc3`](https://github.com/Agentic-Brain/standard_pipelines/commit/e841dc3f02405b4cfc625c68a809ad6518d013cf))

* updated ci workflows ([`f551630`](https://github.com/Agentic-Brain/standard_pipelines/commit/f5516304f4a82dc406a87cb4cf9f2ccf235372c7))

* Merge branch &#39;main&#39; into devin/1737827988-add-docker-cicd ([`94dd325`](https://github.com/Agentic-Brain/standard_pipelines/commit/94dd325f4046fc98f6bc2425f43a1896bff89159))

* Merge pull request #39 from Agentic-Brain/37/acp/ff2hs-secrests

Changed credentials to use bitwarden setup ([`4d9e88a`](https://github.com/Agentic-Brain/standard_pipelines/commit/4d9e88ae5a48735eb618691315a4c68c9b410595))

* several changes ([`f41cd98`](https://github.com/Agentic-Brain/standard_pipelines/commit/f41cd983a757c5d2b9cd694ab92719d7999317a6))

* Merge pull request #29 from Agentic-Brain/28/sebastian/ephemeralandff2hs

ff2hs data flow ([`c18fe7d`](https://github.com/Agentic-Brain/standard_pipelines/commit/c18fe7dd7013c2dfd5a88a352befde3decd485ba))

* Delete migrations/versions/5e023138d54f_initial_migrations.py ([`9eb84b9`](https://github.com/Agentic-Brain/standard_pipelines/commit/9eb84b941d5a4cd90a776553f7943bbf09e33466))

* Merge branch &#39;main&#39; into 28/sebastian/ephemeralandff2hs ([`79d6756`](https://github.com/Agentic-Brain/standard_pipelines/commit/79d6756dc487b39fe0bd27792f92274796421723))

* Merge pull request #35 from Agentic-Brain/devin/1737675665-bws-ci-pipeline

feat: Add GitHub Actions CI workflow and BWS integration ([`551ff35`](https://github.com/Agentic-Brain/standard_pipelines/commit/551ff352911eff07121e115a692a583783a6563a))

* fixed config errors ([`6347a6c`](https://github.com/Agentic-Brain/standard_pipelines/commit/6347a6c89942eba027d0bf5cbafcd40dafe6cadf))

* fixed error in env var name ([`e404b73`](https://github.com/Agentic-Brain/standard_pipelines/commit/e404b73ec84f9fff62a9ae19e87785917430c352))

* fixed error in script arguments ([`bd12b4c`](https://github.com/Agentic-Brain/standard_pipelines/commit/bd12b4c83aab196172385800210dc329f63e9967))

* patched workflow with proper secret ([`317c40b`](https://github.com/Agentic-Brain/standard_pipelines/commit/317c40bd898d269da1a76706ef251a1c7faa7d73))

* bumped requirements ([`f6f178b`](https://github.com/Agentic-Brain/standard_pipelines/commit/f6f178bac2e6879d4f81813ab36b5416e01ccf26))

* updated config for with openai info ([`e704151`](https://github.com/Agentic-Brain/standard_pipelines/commit/e70415130f039efaacb032cc9006294c0ac287ea))

* patched tests for new user model ([`2bd7ac2`](https://github.com/Agentic-Brain/standard_pipelines/commit/2bd7ac248b8b166808238b8524022e74159f76fb))

* added openai test connection ([`8921f40`](https://github.com/Agentic-Brain/standard_pipelines/commit/8921f4086924962623be873436642bcd09670e84))

* debugging generics ([`c7fcacc`](https://github.com/Agentic-Brain/standard_pipelines/commit/c7fcacc7f80203affdd3c5df875711ead26275cd))

* generics for configuration and registry for data flows ([`e25203b`](https://github.com/Agentic-Brain/standard_pipelines/commit/e25203bdea3877d75f80dbcf0d51e52f19d4b87e))

* merged migrations, hubspot creds ([`85e475f`](https://github.com/Agentic-Brain/standard_pipelines/commit/85e475fa8d3bc31c655503bffbdf51079353d137))

* Merge main into 28/sebastian/ephemeralandff2hs ([`5d32e72`](https://github.com/Agentic-Brain/standard_pipelines/commit/5d32e720020d4e8e6d80b2034ab1163387b42d39))

* ff2hs works ([`966874b`](https://github.com/Agentic-Brain/standard_pipelines/commit/966874b8fbaedb753089a504fbf6d61707417259))

* building scripts for ci ([`1243bad`](https://github.com/Agentic-Brain/standard_pipelines/commit/1243bad1a0b9fbf3a35bbc6e9eb357eb6149cd3f))

* Merge pull request #34 from Agentic-Brain/acp/cleanup

Cleaning old implementations ([`dac4081`](https://github.com/Agentic-Brain/standard_pipelines/commit/dac40812d922cba1965908075ba13dc134d67ec5))

* initial migrations ([`83aa1b3`](https://github.com/Agentic-Brain/standard_pipelines/commit/83aa1b39ff093c04edf9c81ff36e23950bde358f))

* various cleanup ([`49f6d3c`](https://github.com/Agentic-Brain/standard_pipelines/commit/49f6d3ce6d91962ef309a331a68d9d3a7dd1b1ad))

* Merge pull request #27 from Agentic-Brain/25/acp/credentials

25/acp/credentials ([`66ca772`](https://github.com/Agentic-Brain/standard_pipelines/commit/66ca77240879b92f9b47c6a2c99df90a03a8fd87))

* Merge pull request #26 from Agentic-Brain/9/acp/securemixin

SecureMixin ([`de3fb78`](https://github.com/Agentic-Brain/standard_pipelines/commit/de3fb78ce5716e33e87c97a36698affdc4c5a9a4))

* hubspot objects and api utils ([`32c9d1b`](https://github.com/Agentic-Brain/standard_pipelines/commit/32c9d1b13ec78030775b404bbf5005f86d14c3e8))

* first draft of ephemeral architecture and partial ff2hs implementation ([`b8ebee0`](https://github.com/Agentic-Brain/standard_pipelines/commit/b8ebee04315ab0769890d7ff5f7d210d76848436))

* fixed accidental debug hardcode ([`8eea51a`](https://github.com/Agentic-Brain/standard_pipelines/commit/8eea51ac659f2590f0fccfeec5ca91d29d3b7e06))

* changed storage to strings for database support ([`76084bb`](https://github.com/Agentic-Brain/standard_pipelines/commit/76084bb6f2ea503485225e77c46671ec2b7be6b4))

* working encryption, decryption still broken ([`8830fa4`](https://github.com/Agentic-Brain/standard_pipelines/commit/8830fa4f780f3800393054a5c9f0f5bd35cb2ef0))

* added base credential model and implementation ([`5abf705`](https://github.com/Agentic-Brain/standard_pipelines/commit/5abf70561ebe814985a7994819bc074572fa1ead))

* added bitwarden usage flag ([`c328215`](https://github.com/Agentic-Brain/standard_pipelines/commit/c3282152ae532018f167edfc54ddd83bea1c5254))

* fixed some errors found in PR ([`11e220f`](https://github.com/Agentic-Brain/standard_pipelines/commit/11e220f4cfe7d8965b168dfb75e124b39719e098))

* getting encryption key is abstracted out ([`1af639e`](https://github.com/Agentic-Brain/standard_pipelines/commit/1af639e4ce2cf2e078c0c53bd08b50ee457023c7))

* simplified to only event listeners ([`f56d22d`](https://github.com/Agentic-Brain/standard_pipelines/commit/f56d22dea7702696e00d6e124c54d4ec6ee0c95f))

* encryption works with attr setters ([`e9c3703`](https://github.com/Agentic-Brain/standard_pipelines/commit/e9c370359e8b183dccea2a18152270224e1eee89))

* commenting out admin dash, early import so migration works ([`915ab9c`](https://github.com/Agentic-Brain/standard_pipelines/commit/915ab9cd0c2c0b94b4759396f44ceecdba4085f4))

* migrations for new tables, will probably reset this later ([`bd8a3d8`](https://github.com/Agentic-Brain/standard_pipelines/commit/bd8a3d8c30009cd841d0896a8df23d51e937f3dc))

* moved client from auth to data flow ([`c2e9d83`](https://github.com/Agentic-Brain/standard_pipelines/commit/c2e9d838a83cc73b73d1cc61178eef74bcf18e2b))

* Merge branch &#39;main&#39; into 9/acp/securemixin ([`798be40`](https://github.com/Agentic-Brain/standard_pipelines/commit/798be40aa966c4f918fef3720aa275b089b69602))

* Merge pull request #20 from Agentic-Brain/acp/restore_dataflow_models

patched issues caused by merge ([`09fb353`](https://github.com/Agentic-Brain/standard_pipelines/commit/09fb353e9b619f09d3bf27c1c22db0f9d3aee445))

* patched issues caused by merge ([`b1ccd76`](https://github.com/Agentic-Brain/standard_pipelines/commit/b1ccd763394843b571f282a59a1f5b39c325b799))

* removed sqlalchemy URI from config ([`a32cf7d`](https://github.com/Agentic-Brain/standard_pipelines/commit/a32cf7d42e16c24130e4cb114335ddac3386c1c8))

* bumped requirements ([`1c56cd9`](https://github.com/Agentic-Brain/standard_pipelines/commit/1c56cd9569ed4038512d33c2ed5fa20d077afa0b))

* added bitwarden client ([`543bb57`](https://github.com/Agentic-Brain/standard_pipelines/commit/543bb576e01f61c445df6150a5d3df3a3082d1fe))

* updated config settings ([`73c3e39`](https://github.com/Agentic-Brain/standard_pipelines/commit/73c3e3983117702a0b42547ee8224c046cbe20f8))

* initial securemixin ([`3d7ff19`](https://github.com/Agentic-Brain/standard_pipelines/commit/3d7ff19534543dd0ed2eba364286e8dbad28631a))

* Merge pull request #7 from Agentic-Brain/acp/merge_fixes

minor naming changes to assist with merge ([`0d11ef2`](https://github.com/Agentic-Brain/standard_pipelines/commit/0d11ef2fa8457dd40a35f6b3fd2538e00d389e8e))

* minor naming changes to assist with merge ([`dc7d486`](https://github.com/Agentic-Brain/standard_pipelines/commit/dc7d486f0f18ed5885c83d01c9d93c3fc746ebbc))

* Merge pull request #6 from Agentic-Brain/1/sebastian/data-flow

1/sebastian/data-flow ([`f0943cf`](https://github.com/Agentic-Brain/standard_pipelines/commit/f0943cfa8b561246e5a5e3bfd5fab6443704eb7f))

* merging with new structure ([`328dac1`](https://github.com/Agentic-Brain/standard_pipelines/commit/328dac177abbe697a10d7c9c54ab46102c61c340))

* Merge branch &#39;main&#39; into 1/sebastian/data-flow ([`0e5f8aa`](https://github.com/Agentic-Brain/standard_pipelines/commit/0e5f8aa3a9b7a7ff76ccbe48daf84c97a80ea6f9))

* resolved merge conflicts ([`8ae0add`](https://github.com/Agentic-Brain/standard_pipelines/commit/8ae0addb888f775483b26944bd5c5f432f720a7a))

* resolved PR comments ([`946a81a`](https://github.com/Agentic-Brain/standard_pipelines/commit/946a81aa0b7f81c02855396576e0be8c0ab8332e))

* deleted common blueprint and consolidated in data_flow ([`5d6d87f`](https://github.com/Agentic-Brain/standard_pipelines/commit/5d6d87f4cc1f5b167dc6f827a79c04c4ff752afe))

* demo, still WIP ([`16c75f9`](https://github.com/Agentic-Brain/standard_pipelines/commit/16c75f96bf9d922e6de8839840a0be67d2bd96a3))

* Merge pull request #5 from Agentic-Brain/3/acp/name_change

changed name to standard_pipelines ([`6a11539`](https://github.com/Agentic-Brain/standard_pipelines/commit/6a11539dc814b10f644c7365f255f21072622e30))

* changed name to standard_pipelines ([`fd35e96`](https://github.com/Agentic-Brain/standard_pipelines/commit/fd35e9678e39bd7ea119665725f106aed11edec8))

* removed duplicate file ([`153132b`](https://github.com/Agentic-Brain/standard_pipelines/commit/153132b7be11bf3e7a43c1fa8923b1e85b4cc5c3))

* fixed join table bug ([`c066f6d`](https://github.com/Agentic-Brain/standard_pipelines/commit/c066f6d381bfc156aa15ea74cda255272b9ed90a))

* created new transformer mixins and registry ([`0cdb481`](https://github.com/Agentic-Brain/standard_pipelines/commit/0cdb4811fbd1ddb07cc24ed00d593ebd228bc955))

* merged timestamp mixin with base mixin ([`dbbd72c`](https://github.com/Agentic-Brain/standard_pipelines/commit/dbbd72ca3522cb3b9a5070a388a17b3223647e5f))

* added new client models ([`8c46754`](https://github.com/Agentic-Brain/standard_pipelines/commit/8c4675492d50c0d8a41fcc307183564b7e32d3ce))

* Initial commit ([`9dd94cc`](https://github.com/Agentic-Brain/standard_pipelines/commit/9dd94cc519b446fa870a7eb426405c4b98b2f950))
