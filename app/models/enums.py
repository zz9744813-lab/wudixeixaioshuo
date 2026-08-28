"""Frozen protocol enumerations (spec §5, §9–§15, §26, §33, §36).

These are the controlled vocabularies every Agent, table and API must speak.
They are intentionally explicit (no magic strings) so research data stays
machine-checkable and gradeable against the spec.
"""
from __future__ import annotations

import enum


class SourceClass(str, enum.Enum):
    """Research corpus vs AI-generated text must never be conflated (P-09)."""
    HUMAN_ORIGINAL = "human_original"
    HUMAN_EDITED = "human_edited"
    AI_GENERATED = "ai_generated"
    AI_REWRITTEN = "ai_rewritten"
    EXPERIMENTAL_COUNTERFACTUAL = "experimental_counterfactual"
    PRODUCTION_NOVELFORGE = "production_novelforge"
    USER_FEEDBACK = "user_feedback"


class KnowledgeStatus(str, enum.Enum):
    """Same Fact may hold different statuses per character (spec §10)."""
    UNKNOWN = "UNKNOWN"
    EXPOSED = "EXPOSED"
    SUSPECTED = "SUSPECTED"
    BELIEVED = "BELIEVED"
    KNOWN = "KNOWN"
    DISBELIEVED = "DISBELIEVED"
    FALSE_BELIEF = "FALSE_BELIEF"
    FORGOTTEN = "FORGOTTEN"
    AMBIGUOUS = "AMBIGUOUS"


class KnowledgeTier(str, enum.Enum):
    """Knowledge promotion ladder (spec §26). Only VALIDATED+ may feed production (P-10)."""
    OBSERVATION = "OBSERVATION"
    CANDIDATE = "CANDIDATE"
    SUPPORTED = "SUPPORTED"
    REPLICATED = "REPLICATED"
    VALIDATED = "VALIDATED"
    PRODUCTION_PROVEN = "PRODUCTION_PROVEN"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"


class TaskStatus(str, enum.Enum):
    """Task / Run state machine (spec §33)."""
    PENDING = "PENDING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_FINAL = "FAILED_FINAL"
    CANCELLED = "CANCELLED"


class ConfidenceLevel(str, enum.Enum):
    """Explicit uncertainty vocabulary (spec §71)."""
    KNOWN = "known"
    LIKELY = "likely"
    UNCERTAIN = "uncertain"
    AMBIGUOUS = "ambiguous"
    CONTRADICTORY = "contradictory"


class EventType(str, enum.Enum):
    """Event must be a state change (spec §8). Multi-label allowed."""
    PHYSICAL = "physical"
    SPEECH = "speech"
    PERCEPTION = "perception"
    INFORMATION = "information"
    DECISION = "decision"
    RELATIONSHIP = "relationship"
    EMOTIONAL = "emotional"
    GOAL_CHANGE = "goal_change"
    REVEAL = "reveal"
    CONCEALMENT = "concealment"
    PROMISE = "promise"
    BETRAYAL = "betrayal"
    FAILURE = "failure"
    SUCCESS = "success"
    ARRIVAL = "arrival"
    DEPARTURE = "departure"
    CONFLICT = "conflict"
    RESOLUTION = "resolution"


class NarrativeFunction(str, enum.Enum):
    """Each Scene may serve several structural functions (spec §14)."""
    SETUP = "setup"
    ESCALATION = "escalation"
    REVEAL = "reveal"
    PAYOFF = "payoff"
    FORESHADOW = "foreshadow"
    MISDIRECTION = "misdirection"
    RELATIONSHIP_SHIFT = "relationship_shift"
    CHARACTERIZATION = "characterization"
    WORLDBUILDING = "worldbuilding"
    BREATHER = "breather"
    TRANSITION = "transition"
    DECISION = "decision"
    FAILURE = "failure"
    VICTORY = "victory"
    REVERSAL = "reversal"
    CLIMAX = "climax"
    AFTERMATH = "aftermath"
    HOOK = "hook"


class CausalEdgeType(str, enum.Enum):
    """Causal edge types; adjacency is NOT automatic causation (spec §13)."""
    PHYSICAL_CAUSE = "physical_cause"
    INFORMATIONAL_CAUSE = "informational_cause"
    PSYCHOLOGICAL_CAUSE = "psychological_cause"
    SOCIAL_CAUSE = "social_cause"
    RESOURCE_CAUSE = "resource_cause"
    GOAL_CAUSE = "goal_cause"
    CONSTRAINT_CAUSE = "constraint_cause"
    AUTHORIAL_STRUCTURE = "authorial_structure"
    TEMPORAL_ONLY = "temporal_only"
    CORRELATION_ONLY = "correlation_only"


class TechniqueCategory(str, enum.Enum):
    """First-level technique taxonomy (spec §15.2)."""
    INFORMATION = "Information"
    SUSPENSE = "Suspense"
    MYSTERY = "Mystery"
    FORESHADOW = "Foreshadow"
    REVEAL = "Reveal"
    PAYOFF = "Payoff"
    CONFLICT = "Conflict"
    ESCALATION = "Escalation"
    CHARACTERIZATION = "Characterization"
    RELATIONSHIP = "Relationship"
    EMOTION = "Emotion"
    PACING = "Pacing"
    DIALOGUE = "Dialogue"
    POV = "POV"
    SCENE_STRUCTURE = "Scene Structure"
    CHAPTER_HOOK = "Chapter Hook"
    WORLDBUILDING = "Worldbuilding"
    ACTION = "Action"
    COMEDY = "Comedy"
    HORROR = "Horror"
    ROMANCE = "Romance"
    EROTIC_TENSION = "Erotic Tension"
    TRAGEDY = "Tragedy"
    TWIST = "Twist"
    MISDIRECTION = "Misdirection"
    REWARD = "Reward"
    LOSS = "Loss"
    PROGRESSION = "Progression"
    POWER_FANTASY = "Power Fantasy"


class RelationshipDimension(str, enum.Enum):
    """A relationship is not a single 'like' score (spec §11)."""
    TRUST = "trust"
    ATTACHMENT = "attachment"
    RESPECT = "respect"
    ADMIRATION = "admiration"
    FEAR = "fear"
    RESENTMENT = "resentment"
    DEPENDENCY = "dependency"
    OBLIGATION = "obligation"
    COMPETITION = "competition"
    JEALOUSY = "jealousy"
    INTIMACY = "intimacy"
    SEXUAL_TENSION = "sexual_tension"
    POWER = "power"
    PREDICTABILITY = "predictability"


class EmotionType(str, enum.Enum):
    """Emotion must carry trigger + appraisal, never a bare label (spec §12)."""
    ANGER = "anger"
    SADNESS = "sadness"
    FEAR = "fear"
    JOY = "joy"
    ANXIETY = "anxiety"
    SHAME = "shame"
    GUILT = "guilt"
    JEALOUSY = "jealousy"
    HOPE = "hope"
    DISAPPOINTMENT = "disappointment"
    SURPRISE = "surprise"
    CONTEMPT = "contempt"
    PRIDE = "pride"
    RELIEF = "relief"
    CURIOSITY = "curiosity"
    TENDERNESS = "tenderness"
    CONFUSION = "confusion"
    NUMBNESS = "numbness"


class AppraisalDimension(str, enum.Enum):
    """Appraisal dimensions feeding the emotion chain (spec §12.2)."""
    GOAL_RELEVANCE = "goal_relevance"
    GOAL_CONGRUENCE = "goal_congruence"
    AGENCY = "agency"
    BLAME = "blame"
    CERTAINTY = "certainty"
    CONTROL = "control"
    NOVELTY = "novelty"
    NORM_COMPATIBILITY = "norm_compatibility"
    SELF_IMAGE_THREAT = "self_image_threat"
    RELATIONSHIP_THREAT = "relationship_threat"
    LOSS_MAGNITUDE = "loss_magnitude"
    FUTURE_CONSEQUENCE = "future_consequence"


class EvidenceType(str, enum.Enum):
    """Evidence provenance types (spec §17.2)."""
    DIRECT_TEXT = "direct_text"
    DIALOGUE = "dialogue"
    BEHAVIOR = "behavior"
    NARRATION = "narration"
    STATE_TRANSITION = "state_transition"
    CROSS_SCENE = "cross_scene"
    EXTERNAL_ANNOTATION = "external_annotation"
    HUMAN_FEEDBACK = "human_feedback"
    EXPERIMENTAL_RESULT = "experimental_result"


class HypothesisStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"
    TESTING = "TESTING"
    SUPPORTED = "SUPPORTED"
    REJECTED = "REJECTED"
    REPLICATED = "REPLICATED"


class ExperimentStatus(str, enum.Enum):
    DESIGNED = "DESIGNED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"


class VariantType(str, enum.Enum):
    CONTROL = "control"
    TREATMENT = "treatment"


class ArtifactType(str, enum.Enum):
    SCENE_GENOME = "scene_genome"
    CHARACTER_TIMELINE = "character_timeline"
    CAUSAL_GRAPH = "causal_graph"
    TECHNIQUE_CARD = "technique_card"
    HYPOTHESIS_REPORT = "hypothesis_report"
    EXPERIMENT_REPORT = "experiment_report"
    ROLLOUT_TREE = "rollout_tree"
    BENCHMARK_RESULT = "benchmark_result"
    REPORT = "report"
    RAW_OUTPUT = "raw_output"


class EvaluationType(str, enum.Enum):
    PAIRWISE = "pairwise"
    ABSOLUTE = "absolute"
    READER_SIM = "reader_sim"
    RULE_EVAL = "rule_eval"
    BENCHMARK = "benchmark"


class BenchName(str, enum.Enum):
    CHARACTER_BENCH = "CharacterBench"
    CAUSAL_BENCH = "CausalBench"
    EMOTION_BENCH = "EmotionBench"
    INFO_GAP_BENCH = "InfoGapBench"
    SUSPENSE_BENCH = "SuspenseBench"
    LONG_STORY_BENCH = "LongStoryBench"


class ForeshadowStatus(str, enum.Enum):
    PLANTED = "PLANTED"
    REINFORCED = "REINFORCED"
    DORMANT = "DORMANT"
    PAYOFF_READY = "PAYOFF_READY"
    PAID = "PAID"
    ABANDONED = "ABANDONED"
    CONTRADICTED = "CONTRADICTED"


class ConflictType(str, enum.Enum):
    INTERNAL = "internal"
    INTERPERSONAL = "interpersonal"
    EXTERNAL = "external"
    SOCIETAL = "societal"


class ResearchEdgeType(str, enum.Enum):
    """Edges of the Research Knowledge Graph (spec §27)."""
    CONTAINS = "CONTAINS"
    OBSERVED_IN = "OBSERVED_IN"
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    DERIVED_FROM = "DERIVED_FROM"
    TESTS = "TESTS"
    CAUSES = "CAUSES"
    AFFECTS = "AFFECTS"
    APPLIES_TO = "APPLIES_TO"
    FAILS_IN = "FAILS_IN"
    REPLICATES = "REPLICATES"
