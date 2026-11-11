"""Current Core turn -> consented, explicitly tentative share-feedback pair."""
from collections import OrderedDict
import json
import threading


FEEDBACK_SCHEMA = {
    'name':'alive_record_feedback',
    'description':'Remember clear feedback about one retained Alive share in this current owner message, '
        'only when Alive context says feedback capture is enabled. Use its exact reference and a contiguous '
        'evidence_span from the current message. Explain why it concerns that share in association_reason. '
        'This is your semantic association, not proof of a platform quote or permanent preference. '
        'Do not record casual topical followups, third-party quotations or ambiguous evaluations; ask if unclear. '
        'Preserve situational qualifications and negations. Acknowledge the evaluation at the scope in the '
        'tool result. Reserve promises about future behavior for confirmed changes. '
        'Use topic_reaction only for an explicit reaction to the share subject or example. '
        'Use unclear for a presentation-only request, mixed reaction or ambiguous topic value. '
        'The tool retains the exact current message for the guided bounded period, not other chat history.',
    'parameters':{'type':'object','properties':{
        'reference':{'type':'string'}, 'evidence_span':{'type':'string'},
        'association_reason':{'type':'string'},
        'topic_reaction':{'type':'string','enum':['positive','negative','unclear'],
            'description':'Tentative reaction to the subject of this share. Exclude presentation requests.'}},
        'required':['reference','evidence_span','association_reason'],'additionalProperties':False}}


class CoreFeedbackBridge:
    def __init__(self,binding):
        self.binding=binding
        self.turns=OrderedDict()
        self.observed=OrderedDict()
        self.lock=threading.RLock()

    def close(self):
        with self.lock:
            self.turns.clear();self.observed.clear()

    def admitted_input(self,scope,revision):
        with self.lock:
            key=(scope,revision)
            if key in self.observed:return
            self.observed[key]=True
            while len(self.observed)>128:self.observed.popitem(last=False)
            for previous in tuple(self.turns):
                if previous[0]==scope:del self.turns[previous]

    def _owner(self,scope):
        from .kernel_execution_bridge import configured_owner,runtime_engine
        if self.binding.closed or runtime_engine(self.binding)!='kernel':
            raise ValueError('current native feedback generation required')
        self.binding._require_home()
        return configured_owner(self.binding,scope)

    def context(self,**values):
        from .kernel_execution_bridge import kernel
        continuity=self.binding._continuity
        if self.binding.closed or continuity is None:return None
        scope=continuity.router.scope_for_hook(values)
        task,turn,text=values.get('task_id'),values.get('turn_id'),values.get('user_message')
        if (scope is None or not isinstance(task,str) or not 1<=len(task)<=4096
                or not isinstance(turn,str) or not 1<=len(turn)<=4096
                or not isinstance(text,str) or not 1<=len(text)<=8000):return None
        history=values.get('conversation_history')
        current=history[-1] if isinstance(history,list) and history else None
        message_id=current.get('platform_message_id') if isinstance(current,dict) and current.get('role')=='user' else None
        if not isinstance(message_id,str) or not 1<=len(message_id)<=4096:return None
        store,configured=self._owner(scope)
        feedback=kernel('native_feedback')
        enabled,permission_id=feedback.permission(store,configured)
        if not enabled:return None
        admission=feedback.admitted_input(store,configured,text,message_id)
        if admission is None:return None
        shares=continuity.store.read(scope=scope.binding_document(),clearance=continuity.clearance,
            include_sources=False)
        references=[continuity._reference(scope,task,item['share_id']) for item in shares
                    if item['submission_status']=='success_reported']
        if not references:return None
        with self.lock:
            for previous in tuple(self.turns):
                if previous[0]==scope and previous[2]!=turn:del self.turns[previous]
            self.turns[(scope,task,turn)]=(configured.event_id,permission_id,admission.event.event_id,text,message_id)
            while len(self.turns)>64:self.turns.popitem(last=False)
        return {'context':'Alive share-feedback capture and interpretation is enabled for this owner. '
            'If this current message clearly evaluates a retained share, use alive_record_feedback with its '
            'reference and an exact evidence span. This records your tentative semantic association; '
            'it does not establish a platform quote, human seeing or permanent interest. Preserve scope: '
            'a one-off length comment is not an always-short rule, and being busy is not dislike. '
            'For a topical followup just continue the conversation; for unclear targets ask. '
            'Never claim you learned from a message unless the tool succeeded. References: '
            +json.dumps(references,separators=(',',':'))}

    def tool(self,args,*,task_id=None,session_id=None,**_ignored):
        try:
            from .kernel_execution_bridge import kernel
            from gateway.session_context import get_session_env
            from tools import approval_context
            continuity=self.binding._continuity
            required={'reference','evidence_span','association_reason'}
            if (self.binding.closed or continuity is None or not isinstance(args,dict)
                    or not required<=set(args)<=required|{'topic_reaction'}):
                raise ValueError('current feedback operation required')
            scope=continuity.router.scope_for_hook(dict(session_id=session_id,
                sender_id=get_session_env('HERMES_SESSION_USER_ID'),
                platform=get_session_env('HERMES_SESSION_PLATFORM')))
            turn=approval_context._approval_turn_id.get()
            if scope is None or approval_context._approval_session_id.get()!=session_id:
                raise ValueError('Core turn binding unavailable')
            with self.lock:
                ticket=self.turns.get((scope,task_id,turn))
            with continuity._reference_lock:
                reference=continuity._references.get(args['reference'])
            if ticket is None or reference is None or reference[:2]!=(scope,task_id):
                raise ValueError('feedback target not in this turn')
            store,configured=self._owner(scope)
            if ticket[0]!=configured.event_id:raise ValueError('feedback configuration changed')
            def validate():
                from .kernel_execution_bridge import runtime_engine
                if self.binding.closed or runtime_engine(self.binding)!='kernel':
                    raise ValueError('feedback generation changed')
                self.binding._require_home()
                with self.lock:
                    if self.turns.get((scope,task_id,turn))!=ticket:
                        raise ValueError('feedback turn superseded')
                if continuity.router.scope_for_hook(dict(session_id=session_id,
                        sender_id=get_session_env('HERMES_SESSION_USER_ID'),
                        platform=get_session_env('HERMES_SESSION_PLATFORM')))!=scope:
                    raise ValueError('feedback route changed')
            recorded=kernel('native_feedback').NativeFeedbackStore(continuity.store).record(
                configured=configured,scope=scope.binding_document(),admission_id=ticket[2],
                share_id=reference[2],text=ticket[3],permission_id=ticket[1],message_id=ticket[4],
                evidence_span=args['evidence_span'],association_reason=args['association_reason'],
                validate_current=validate,topic_reaction=args.get('topic_reaction'))
            result=dict(status='recorded_tentative_share_feedback',event_id=recorded.event.event_id,
                feedback_scope='referenced_share',future_behavior_committed=False,
                automatic_profile_update=False,action_authority=False,
                attribution='main_turn_semantic_association_not_quote_proof')
        except (ValueError,KeyError,TypeError,AttributeError):
            result={'error':'alive_feedback_unavailable','hint':
                'Use a current consented owner turn and its exact retained share reference; '
                'do not guess a target or claim this feedback was saved.'}
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning('Alive feedback recording failed: %s',type(exc).__name__)
            result={'error':'alive_feedback_unavailable','hint':'This feedback was not confirmed saved.'}
        return json.dumps(result,ensure_ascii=False,separators=(',',':'))
