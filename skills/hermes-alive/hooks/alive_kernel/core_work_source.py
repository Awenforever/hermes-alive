"""Current owned agenda sources for Core work; no model or execution authority."""
from contextlib import closing
from datetime import datetime,timezone
import json

from .core_work import CoreWorkStore


class OwnedWorkSource:
    def __init__(self,store):self.store=store;self.work=CoreWorkStore(store)

    def authority(self,configured):
        self.work._home()
        if self.store.configuration()!=configured or configured.options.get('core_background_work') is not True:
            raise ValueError('current guided Core work grant required')
        from .autonomy_policy import AutonomyPolicyProjection
        from .transport_reconciliation_runtime import TransportReconciliationRuntime
        policies=AutonomyPolicyProjection(self.store.journal);policies.project_new()
        policy=TransportReconciliationRuntime.canonical_owner_policy(policies,self.store.journal,configured.subject)
        if not policy.enabled:raise ValueError('owned autonomous work is paused')
        return policy

    def item(self,item_id,configured,*,include_source=False):
        from .cognition_opportunities import CognitionOpportunityReader
        now=datetime.now(timezone.utc)
        with closing(self.store.journal._connect()) as c:
            row=c.execute('SELECT * FROM agenda_items_v1 WHERE item_id=? AND subject=?',
                (item_id,configured.subject)).fetchone()
            transition=c.execute('SELECT caused_by_event_id FROM agenda_transitions_v1 WHERE item_id=? '
                'ORDER BY transition_id DESC LIMIT 1',(item_id,)).fetchone()
        if row is None or transition is None or not row['expires_at']:return None
        evidence=CognitionOpportunityReader(self.store.journal,content_vault=self.store.vault)._commitment(
            row,subject=configured.subject,now=now)
        if evidence is None or row['state'] not in ('active','snoozed'):return None
        if row['available_at'] and datetime.fromisoformat(row['available_at'])>now:return None
        if datetime.fromisoformat(row['expires_at'])<=now:return None
        version=self.store.protector.authenticate_json('alive.agenda.item_version.v1',{
            'configuration':configured.event_id,'owner':configured.subject,'item':item_id,'event':transition[0]})
        result={'item_id':item_id,'item_version':version,'details':json.loads(evidence.content['summary'])['commitment'],
            'due_at':row['due_at'],'expires_at':row['expires_at']}
        if include_source:
            original=evidence.content.get('original_owner_message')
            if (evidence.content.get('original_source_available') is not True
                    or not isinstance(original,str) or not original.strip() or len(original)>6000):return None
            result.update(original_owner_request=original,owner_source_event_id=evidence.content['source_event_id'],
                source_recorded_at=evidence.content['source_recorded_at'],
                source_retention_until=evidence.content['original_source_retention_until'])
        return result
