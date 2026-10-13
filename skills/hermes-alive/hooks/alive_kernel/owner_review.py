"""Personal-owner operation linkage; not a gateway authentication substitute."""


def owner_review_source(journal, event, target):
    """Return a causally ordered owner input, never authority from a cache row.

    The caller supplies a canonical target JournalRecord. The source and review
    must both belong to that target's owner. Actor equality is necessary but
    cannot authenticate a writer that can forge the owner's principal string.
    """
    original = journal.get(event.event_id)
    source = journal.get(str(event.payload.get("source_event_id") or ""))
    owner = target.event.subject if target is not None else None
    if (
        original is None or original.event != event or source is None or not owner
        or not target.sequence < source.sequence < original.sequence
        or source.event.event_type != "conversation.inbound"
        or event.actor != owner or source.event.actor != owner
        or event.subject != owner or source.event.subject != owner
        or event.sensitivity != target.event.sensitivity
        or event.causation_id != source.event.event_id
        or not target.event.observed_at <= source.event.observed_at <= event.observed_at
    ):
        return None
    return source
