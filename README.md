<!-- html for no underline https://github.com/shd101wyy/markdown-preview-enhanced/issues/185#issuecomment-1373553815a -->
<div id="user-content-toc">
<ul>
<summary>
<h1 style="display: inline-block;">
American Causal Inference Conference (ACIC)
<br>
2022 Data Challenge
</h1>
<h2 style="display: inline-block;">
Inverse Probability Weighting Difference-in-Differences (IPWDID)
<br>
<a href="https://www.komodohealth.com"><img src="assets/kh-icon.png" height="26"></a>
<a href="https://www.komodohealth.com">Komodo Health</a>
</h2>
</summary>
</ul>
</div>

## Authors:
<a href="https://www.linkedin.com/in/weiyuqin">Yuqin Wei</a>,
<a href="https://www.linkedin.com/in/matthew-epland">Matthew Epland</a>
and <a href="https://www.linkedin.com/in/jingyuan-hannah-liu">Jingyuan (Hannah) Liu</a>

## Abstract
In this American Causal Inference Conference (ACIC) 2022 challenge submission,
the canonical difference-in-differences (DID) estimator
has been used with inverse probability weighting (IPW)
and strong simplifying assumptions
to produce a benchmark model of the
sample average treatment effect on the treated (SATT).
Despite the restrictive assumptions and simple model,
satisfactory performance in both point estimate and confidence intervals was observed,
ranking in the top half of the competition.

## Paper
Published in [Observational Studies, Volume 9, Issue 3, 2023](https://muse.jhu.edu/issue/50973),
the 2022 ACIC special issue.
- [Published Paper](https://doi.org/10.1353/obs.2023.0027)
- [pdf](https://github.com/mepland/acic_causality_challenge_2022/blob/main/paper/paper_komodo_ipwdid.pdf)

## Prompt
[2022 Challenge Site](https://acic2022.mathematica.org/)


## Cloning the Repository
ssh
```bash
git clone git@github.com:mepland/acic_causality_challenge_2022.git
```

https
```bash
git clone https://github.com/mepland/acic_causality_challenge_2022.git
```

## Installing Dependencies
It is recommended to work in a [python virtual environment](https://realpython.com/python-virtual-environments-a-primer/) to avoid clashes with other installed software.
```bash
python -m venv ~/.venvs/causality
source ~/.venvs/causality/bin/activate
pip install -r requirements.txt
```
