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

    def item(self,item_id,configured,*,include_source=False,require_available=True):
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
        if require_available and row['available_at'] and datetime.fromisoformat(row['available_at'])>now:return None
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

    def existing(self,item_id,configured,version,*,include_source=False):
        """Attention-only transitions do not revoke already admitted work.

        The complete current chain is verified by item/_commitment first. Never
        cross completion, cancellation, expiry or reopening into a new task life.
        New work selection and result assessment still obey availability.
        """
        current=self.item(item_id,configured,include_source=include_source,require_available=False)
        if current is None:return None
        with closing(self.store.journal._connect()) as c:
            rows=c.execute('SELECT caused_by_event_id,to_state FROM agenda_transitions_v1 WHERE item_id=? '
                'ORDER BY transition_id DESC LIMIT 65',(item_id,)).fetchall()
        if not rows or len(rows)>64:return None
        for row in rows:
            if row['to_state'] not in ('active','snoozed'):break
            candidate=self.store.protector.authenticate_json('alive.agenda.item_version.v1',{
                'configuration':configured.event_id,'owner':configured.subject,'item':item_id,
                'event':row['caused_by_event_id']})
            if candidate==version:return current
        return None

    def page(self,configured,*,kind='autonomous-work'):
        if kind not in ('autonomous-work','work-outcomes'):raise ValueError('known work page required')
        self.authority(configured)
        """Rotate a bounded agenda page, including unavailable-source rows."""
        anchor='core-work:'+self.store.protector.authenticate_json('alive.'+kind+'.scan.v1',
            {'owner':configured.subject})
        event_type='work.scan_advanced' if kind=='autonomous-work' else 'work.outcome_scan_advanced'
        with closing(self.store.journal._connect()) as c:
            prior=c.execute("SELECT event_id FROM experience_events WHERE subject=? "
                "AND event_type=? ORDER BY sequence DESC LIMIT 1",(configured.subject,event_type)).fetchone()
            cursor=(self.work._read(anchor,prior[0].removeprefix(anchor+':'),configured.subject,
                event_type=event_type) if prior else None)
            created,item=(cursor['created_at'],cursor['item_id']) if cursor else ('','')
            rows=c.execute("SELECT item_id,created_at FROM agenda_items_v1 WHERE subject=? "
                "AND state IN ('active','snoozed') ORDER BY "
                "CASE WHEN (created_at,item_id)>(?,?) THEN 0 ELSE 1 END,created_at,item_id LIMIT 8",
                (configured.subject,created,item)).fetchall()
        return anchor,rows

    def advance(self,configured,anchor,row,operation_id,*,kind='autonomous-work'):
        if kind not in ('autonomous-work','work-outcomes'):raise ValueError('known work page required')
        self.authority(configured)
        event_type='work.scan_advanced' if kind=='autonomous-work' else 'work.outcome_scan_advanced'
        suffix='scan:'+self.store.protector.authenticate_json('alive.'+kind+'.scan-step.v1',
            {'operation':operation_id,'item':row['item_id']})
        point={'configuration_event_id':configured.event_id,'item_id':row['item_id'],'created_at':row['created_at']}
        existing=self.work._read(anchor,suffix,configured.subject,event_type=event_type)
        if existing is None:self.work._append(anchor,suffix,configured.subject,point,event_type=event_type)
        elif existing!=point:raise ValueError('owned work page changed within a cycle')

