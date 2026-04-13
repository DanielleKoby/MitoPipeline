# Phylogenetics Pipeline Debugging Roadmap (2 Weeks)

**Objective:** Fix incorrect phylogenetic tree topology by addressing critical VCF filtering, variant calling, and tree assembly issues.

**Status:** 🔴 CRITICAL - Three interconnected problems causing tree failures

---

## Week 1: Variant Calling & VCF Filtering (Root Cause Analysis)

### Day 1 (Monday): Diagnostic Review & Verify Mutect2 Status

**Goal:** Understand current data state and confirm variant calling pipeline

**Tasks:**
- [ ] Check if GATK Mutect2 is actually running or if using pre-generated VCFs
  - [ ] List raw VCF files: `ls -lh data/processed/variants/raw/`
  - [ ] Extract variant stats: `zcat data/processed/variants/raw/SAMPLE*.vcf.gz | grep -v "^#" | wc -l`
  - [ ] Check AF distribution in raw VCFs (confirm Mutect2 produced them)
- [ ] Verify filtered VCF exists: `ls -lh data/processed/variants/filtered/`
- [ ] Count variants by AF threshold:
  ```bash
  for file in data/processed/variants/raw/*.vcf.gz; do
    echo "Variants in $file:";
    zcat "$file" | awk -F'\t' 'NR>2 {print $10}' | wc -l;
  done
  ```
- [ ] **Document findings** in working notes

**Checklist:**
- [ ] Confirmed Mutect2 execution or identified pre-existing VCFs
- [ ] Counted total variants in raw/filtered VCFs
- [ ] Identified AF distribution
- [ ] Updated PHYLO_DEBUGGING.md with findings

---

### Day 2 (Tuesday): Analyze VCF-Consensus Mismatch

**Goal:** Verify the AF ≥ 0.4 vs AF ≥ 0.5 consensus mismatch

**Tasks:**
- [ ] **Check filtered VCF AF threshold** (currently 0.4):
  ```bash
  zcat data/processed/variants/filtered/SAMPLE.filtered_mito_calls.vcf.gz | \
    awk -F'\t' 'NR>2 {split($10,f,":"); print f[3]}' | sort -n | uniq -c
  ```
- [ ] **Measure consensus generation behavior:**
  - [ ] For one sample, count variants with 0.4 ≤ AF < 0.5
  - [ ] Check if those positions appear as reference (not alternate) in consensus FASTA
  - [ ] Verify mismatch == variants missing from consensus
- [ ] **Test bcftools consensus default behavior:**
  ```bash
  # What AF threshold does bcftools consensus use by default?
  bcftools consensus -f reference.fa test.vcf | head
  ```
- [ ] **Create comparison table:**
  - Sample ID | Variants in filtered VCF (AF≥0.4) | Variants in consensus FASTA | Mismatch count
- [ ] **Document findings with examples**

**Checklist:**
- [ ] Quantified AF 0.4-0.5 mismatch size
- [ ] Confirmed mutations missing from consensus FASTA
- [ ] Created mismatch comparison table
- [ ] Documented impact on tree assembly

---

### Day 3 (Wednesday): Quality Filter Gap Analysis

**Goal:** Identify missing quality checks causing noise

**Tasks:**
- [ ] **Audit current filters** in `mutect2_haplotyping.sh` (line 113):
  - [ ] Current: `af >= 0.4 && pos > 200 && pos < 16578`
  - [ ] **Missing checks:**
    - [ ] Depth (DP ≤ 20x or DP > 200x are error-prone)
    - [ ] Base quality (QUAL < 50 indicates weak calls)
    - [ ] Strand bias (SB field or StrandBiasBySample)
- [ ] **Check if Mutect2 annotations exist** in raw VCF:
  ```bash
  zcat data/processed/variants/raw/SAMPLE.raw_mito_calls.vcf.gz | \
    grep "^##INFO" | grep -i "strand\|bias\|sb"
  ```
- [ ] **Verify commented-out sections** (lines 38-54 & 64-93):
  - [ ] Are GATK Mutect2 & FilterMutectCalls actually running?
  - [ ] If not, why were they commented out?
  - [ ] What annotations are missing without them?
- [ ] **Estimate noise reduction potential:**
  - [ ] Run test filter with AF≥0.5 on 5 samples
  - [ ] Count variants removed vs kept
  - [ ] Calculate % noise reduction

**Checklist:**
- [ ] Listed all missing quality filters (DP, QUAL, SB)
- [ ] Confirmed Mutect2 status (running or not)
- [ ] Quantified noise from low-AF variants
- [ ] Estimated variant count reduction with stricter thresholds

---

### Day 4 (Thursday): Circular mtDNA Rotation Logic

**Goal:** Assess impact of position 0-200 boundary effects

**Tasks:**
- [ ] **Review rotation variables** (line 16-17):
  ```bash
  ROTATION_STRAT=$MITO_READ_LEN        # 150 bp
  ROTATION_END=$((MITO_SEQ_LEN - MITO_READ_LEN))  # 16578
  ```
- [ ] **Understand why rotation logic exists but isn't used:**
  - [ ] Current filter excludes positions 0-200 & 16578-16728 (read length edges)
  - [ ] Mitochondrial DNA **is circular** → these regions wrap around
  - [ ] Missing logic = variants near boundaries are treated as separate regions
- [ ] **Map excluded variants:**
  ```bash
  # Count variants filtered out by position < 200 or > 16578
  zcat data/processed/variants/raw/SAMPLE.vcf.gz | \
    awk -F'\t' 'NR>2 && $2 <= 200 {print "EXCLUDED_START: " $2}' | wc -l
  zcat data/processed/variants/raw/SAMPLE.vcf.gz | \
    awk -F'\t' 'NR>2 && $2 > 16578 {print "EXCLUDED_END: " $2}' | wc -l
  ```
- [ ] **Assess impact on tree topology:**
  - [ ] Do excluded variants belong to samples with distinct breeds?
  - [ ] Could boundary filtering cause breed clustering artifacts?
- [ ] **Document decision:** Keep exclusion or implement rotation?

**Checklist:**
- [ ] Quantified variants excluded at boundaries
- [ ] Assessed breed-specific impact of boundary filtering
- [ ] Documented rotation logic decision for later implementation

---

### Day 5 (Friday): Create VCF Filtering Standard

**Goal:** Establish new filtering thresholds & implement improvements

**Tasks:**
- [ ] **Define recommended thresholds** (from debugging doc):
  ```bash
  # Option A: Strict homoplasmic
  af >= 0.80 && dp >= 20 && qual >= 50
  
  # Option B: Include high-confidence heteroplasmy
  (af >= 0.80 && dp >= 20 && qual >= 50) OR \
  (af >= 0.30 && af < 0.80 && dp >= 50 && qual >= 60)
  ```
- [ ] **Choose approach** (homoplasmic-only vs. heteroplasmy-aware):
  - [ ] Pros/cons of each
  - [ ] Expected variant count reduction
  - [ ] Impact on tree signal
- [ ] **Update mutect2_haplotyping.sh:**
  - [ ] [ ] Change line 113 from `af >= 0.4` to chosen threshold
  - [ ] [ ] Add depth filter in AWK script
  - [ ] [ ] Add QUAL filter in AWK script
  - [ ] [ ] **DO NOT COMMIT** - only prepare for next week's testing
- [ ] **Create test script:**
  - [ ] Run both thresholds on subset of samples
  - [ ] Compare variant counts
  - [ ] Document expected improvements
- [ ] **Prepare bcftools consensus fix:**
  - [ ] Update line 126-127 to explicitly match VCF threshold
  - [ ] Test on one sample for validation

**Checklist:**
- [ ] Defined new filtering thresholds
- [ ] Analyzed homoplasmy vs. heteroplasmy trade-offs
- [ ] Prepared code updates (not yet committed)
- [ ] Created test plan for Week 2

---

## Week 2: Test, Validate & Tree Assembly Optimization

### Day 6 (Monday): Test New VCF Filters

**Goal:** Validate filtering changes on full dataset

**Tasks:**
- [ ] **Create backup of current filtered VCFs:**
  ```bash
  mkdir -p data/processed/variants/filtered_backup_old_threshold
  cp data/processed/variants/filtered/*.vcf.gz data/processed/variants/filtered_backup_old_threshold/
  ```
- [ ] **Apply new filters** to all samples:
  - [ ] Update threshold to AF ≥ 0.50 (minimum fix)
  - [ ] Re-run mutect2_haplotyping.sh on all samples
  - [ ] Time total processing
- [ ] **Compare variant counts:**
  ```bash
  for old in data/processed/variants/filtered_backup_old_threshold/*.vcf.gz; do
    sample=$(basename "$old")
    old_count=$(zcat "$old" | grep -v "^#" | wc -l)
    new_count=$(zcat "data/processed/variants/filtered/$sample" | grep -v "^#" | wc -l)
    echo "$sample: $old_count → $new_count ($(( (new_count - old_count) * 100 / old_count ))%)"
  done
  ```
- [ ] **Regenerate consensus sequences:**
  - [ ] Re-run bcftools consensus with new filtered VCFs
  - [ ] Verify consensus FASTA files updated
- [ ] **Create QC report:**
  - [ ] Variants removed per sample
  - [ ] Average variant reduction %
  - [ ] Samples with extreme changes (potential issues)

**Checklist:**
- [ ] Backed up original filtered VCFs
- [ ] Applied new AF threshold to all samples
- [ ] Quantified variant reduction
- [ ] Regenerated consensus sequences
- [ ] Created before/after comparison report

---

### Day 7 (Tuesday): Rebuild & Test Tree

**Goal:** Assess tree topology improvement

**Tasks:**
- [ ] **Regenerate MSA:**
  - [ ] Uncomment lines 24-44 in `tree_assembly.sh` (MAFFT alignment)
  - [ ] Combine all consensus fastas: `cat data/processed/consensus/fasta/*.fa > combined.fa`
  - [ ] Run MAFFT alignment: `mafft --auto combined.fa > msa_consensus.fa`
- [ ] **Build phylogenetic tree:**
  - [ ] Run iqtree with current TN+F+I+G4 model
  - [ ] Document bootstrap support values
- [ ] **Compare tree topology to old tree:**
  - [ ] Do samples from same breed now cluster together?
  - [ ] Are bootstrap values improved?
  - [ ] Is tree less star-like (polytomy)?
- [ ] **Document improvements (or lack thereof):**
  - [ ] Save side-by-side tree comparisons
  - [ ] Quantify topology changes

**Checklist:**
- [ ] MSA regenerated with new variants
- [ ] New tree built with iqtree
- [ ] Tree topology compared to baseline
- [ ] Documented tree quality improvements

---

### Day 8 (Wednesday): Test Alternative Tree Models

**Goal:** Verify TN+F+I+G4 is appropriate for mtDNA

**Tasks:**
- [ ] **Run IQ-TREE model selection test:**
  ```bash
  iqtree -s msa_consensus_clean_headers.fa -m TEST -nt AUTO
  ```
  - [ ] This will test 286 models and recommend best
  - [ ] Takes 2-4 hours depending on sample count
- [ ] **Document top 5 recommended models:**
  - [ ] BIC scores for each
  - [ ] How does TN+F+I+G4 rank?
- [ ] **Rebuild tree with best model:**
  ```bash
  # Use model from TEST output, e.g., GTR+R5
  iqtree -s msa_consensus_clean_headers.fa -m GTR+R5 -nt AUTO -redo
  ```
- [ ] **Compare trees (TN+F+I+G4 vs. best model):**
  - [ ] Tree topology differences?
  - [ ] Bootstrap support improvement?
  - [ ] Which model better separates breeds?
- [ ] **Update tree_assembly.sh with best model:**
  - [ ] Change line 48 to use optimized model
  - [ ] Document rationale in code comment

**Checklist:**
- [ ] Ran IQ-TREE model selection (TEST mode)
- [ ] Identified top 5 models & ranked TN+F+I+G4
- [ ] Built 2+ trees with different models
- [ ] Selected & updated best model in code
- [ ] Documented model selection rationale

---

### Day 9 (Thursday): Enable & Test GATK Variant Filters

**Goal:** Restore commented-out quality filtering

**Tasks:**
- [ ] **Uncomment Mutect2 call** (mutect2_haplotyping.sh lines 38-46):
  - [ ] Re-enable GATK Mutect2 with StrandBiasBySample annotation
  - [ ] Run on 2 test samples
  - [ ] Verify raw VCF has SB annotations
- [ ] **Uncomment FilterMutectCalls** (lines 50-54):
  - [ ] Re-enable GATK filtering step
  - [ ] Compare raw vs. filtered variant counts
  - [ ] Check PASS/FAIL flags in VCF
- [ ] **Compare GATK filtering vs. our AWK filter:**
  - [ ] Variants kept by GATK but not by AWK?
  - [ ] Variants kept by AWK but not by GATK?
  - [ ] Recommend which to use as primary
- [ ] **Decision:** Use GATK pipeline or keep custom AWK?
  - [ ] If GATK: update script and re-process all samples
  - [ ] If custom: document why custom is preferred

**Checklist:**
- [ ] Tested GATK Mutect2 & FilterMutectCalls
- [ ] Compared GATK vs. custom filtering
- [ ] Made decision on primary filtering method
- [ ] Documented filtering approach in code

---

### Day 10 (Friday): Final Validation & Documentation

**Goal:** Consolidate fixes and prepare for production

**Tasks:**
- [ ] **Full pipeline test run:**
  - [ ] Start with raw BAMs
  - [ ] Run variant calling → filtering → consensus → alignment → tree
  - [ ] Verify each step produces expected outputs
  - [ ] Check processing time & resource usage
- [ ] **Compare tree topology to expected biology:**
  - [ ] Do breed groupings match known canine genetics?
  - [ ] Are purebred samples clustering together?
  - [ ] Is mixed-breed dog in expected position?
- [ ] **Create final QC report:**
  - [ ] Variant counts (before/after filtering)
  - [ ] Consensus sequence stats
  - [ ] Tree topology metrics (bootstrap support, breed separation)
- [ ] **Document all changes:**
  - [ ] Update README.md with new filtering thresholds
  - [ ] Update tree_assembly.sh comments with model selection rationale
  - [ ] List commented-out sections and their status (kept vs. enabled)
- [ ] **Commit changes:**
  - [ ] Create PR with all fixes
  - [ ] Reference PHYLO_DEBUGGING.md findings
  - [ ] List bottlenecks & edge cases still to investigate

**Checklist:**
- [ ] Full pipeline test completed successfully
- [ ] Tree topology validated against known genetics
- [ ] QC report generated
- [ ] Code documentation updated
- [ ] PR created with all changes

---

## Critical Path Dependencies

```
Day 1 (Verify Mutect2) → Day 2 (AF mismatch) → Day 3 (Quality filters)
                              ↓
Day 5 (Define thresholds) → Day 6 (Test filters) → Day 7 (Rebuild tree)
                              ↓                        ↓
Day 8 (Model selection) ← Day 7 (Tree comparison) → Day 9 (GATK filters)
                              ↓
Day 10 (Final validation & commit)
```

---

## Expected Outcomes

### After Week 1:
✅ Root causes identified & quantified  
✅ Decision made on AF threshold & quality filters  
✅ Rotation logic status determined  
✅ Test plan prepared  

### After Week 2:
✅ VCF filtering optimized  
✅ Tree topology improved (breed clustering)  
✅ Tree model optimized for mtDNA  
✅ GATK filtering decision made  
✅ Full pipeline validated  
✅ Changes committed with documentation  

---

## Known Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Stricter AF threshold removes signal | Reduced variants | Test on subset first; compare tree quality |
| Mutect2 runtime increases | Processing time | Run in parallel; use SLURM array jobs |
| Border position filtering artifacts | Breed clustering errors | Assess impact on Day 4; implement rotation if needed |
| Tree model selection takes hours | Week 2 delays | Start model selection early (Day 8 morning) |
| Backward compatibility issues | Results differ from old pipeline | Keep backup VCFs; document threshold change in README |

---

## Success Metrics

- [ ] VCF filtering threshold: AF ≥ 0.50 (or justified alternative)
- [ ] Variants with 0.4 ≤ AF < 0.5 removed from tree: ~90% reduction
- [ ] Tree bootstrap support: >80% at major lineage splits
- [ ] Breed clustering: >80% samples from same breed within monophyletic clade
- [ ] Processing time: <2 hours per sample (including GATK + alignment + tree)
- [ ] Zero commented-out critical code sections (documented status for each)

---

**Last Updated:** April 13, 2026  
**Status:** Ready to execute  
**Next Action:** Start Day 1 diagnostics
