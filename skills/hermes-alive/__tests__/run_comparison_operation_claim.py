"""A durable model-operation claim has one winner across real processes."""
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'hooks'))
from alive_kernel.event_store import ExperienceJournal
from alive_kernel.events import Sensitivity
from alive_kernel.semantic_comparator import SemanticComparator
from alive_kernel.semantic_review import SemanticReviewError


def claim(path):
    comparator=SemanticComparator(SimpleNamespace(journal=ExperienceJournal(Path(path))))
    try:
        clock=comparator._start_authoring('same-operation','user:synthetic','selection:synthetic',
            Sensitivity.PRIVATE,discovery=True,claim=True)
        return ('claimed',clock)
    except SemanticReviewError:return ('refused',None)


def test():
    with tempfile.TemporaryDirectory(prefix='alive-model-operation-') as directory:
        path=Path(directory)/'events.sqlite3'
        ExperienceJournal(path)
        with ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as pool:
            results=list(pool.map(claim,[str(path)]*8))
        assert sum(state=='claimed' for state,_ in results)==1,results
        journal=ExperienceJournal(path)
        rows=journal.read(event_type='semantic.comparison_stage')
        assert len(rows)==1 and rows[0].event.payload['stage']=='started'
        assert claim(str(path))==('refused',None),'cold process regained a consumed claim'
        comparator=SemanticComparator(SimpleNamespace(journal=journal))
        assert comparator._start_authoring('same-operation','user:synthetic','selection:synthetic',
            Sensitivity.PRIVATE,discovery=True)==next(clock for state,clock in results if state=='claimed')
        assert len(journal.read(event_type='semantic.comparison_stage'))==1
    print('HERMES_ALIVE_COMPARISON_OPERATION_CLAIM_OK')


if __name__=='__main__':test()
