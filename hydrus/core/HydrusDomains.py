import os
import threading

from typing import Iterable

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusData



FILE_DOMAIN_KEY = "file_domain"
FILE_DOMAIN_KEY_SERVICE_TYPES = [HC.LOCAL_FILE_DOMAIN]

TAG_DOMAIN_KEY = "TAG_domain"
TAG_DOMAIN_KEY_SERVICE_TYPES = [HC.LOCAL_TAG]

class DomainFilter( HydrusSerialisable.SerialisableBase ):

    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_FILTER
    SERIALISABLE_NAME = 'Domain Filter Rules'
    SERIALISABLE_VERSION = 1

    WOAH_TOO_MANY_RULES_THRESHOLD = 12

    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._lock = threading.Lock()
        
        self._domain_rules: dict[bytes, int] = {}

        self._blacklisted_file_domains: set[bytes] = set()
        self._blacklisted_tag_domains : set[bytes] = set()
        
    def __eq__( self, other ):
        
        if isinstance( other, DomainFilter):
            
            return self._domain_rules == other._domain_rules

        return NotImplemented

    def _GetSerialisableInfo( self ):

        return list( self._domain_rules.items() )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._domain_rules = dict( serialisable_info )
        
        self._UpdateRuleCache()

    def _UpdateRuleCache(self):

        self._blacklisted_file_domains = set()
        self._blacklisted_tag_domains = set()

        for ( service_key, service_type ) in self._domain_rules.items():
            
            if service_type in FILE_DOMAIN_KEY_SERVICE_TYPES:

                self._blacklisted_file_domains.add( service_key )

            elif service_type in TAG_DOMAIN_KEY_SERVICE_TYPES:

                self._blacklisted_tag_domains.add( service_key )
                
        
    def AllowsEverything( self ):
        
        with self._lock:

            return not self._blacklisted_tag_domains and \
                   not self._blacklisted_file_domains


    def CleanRules( self ):
        
        new_domain_rules = {}
        
        for ( service_key, service_type ) in self._domain_rules.items():

            try:

                service = HG.client_controller.service_manager.GetService( service_key )
                service_type = service.GetServiceType()

            except:
                continue
            
            if service_type not in FILE_DOMAIN_KEY_SERVICE_TYPES and service_type not in TAG_DOMAIN_KEY_SERVICE_TYPES:
                continue

            new_domain_rules[service_key] = service_type

        with self._lock:    
            self._tag_slices_to_rules = new_domain_rules

        self._UpdateRuleCache()


    def Filter(self, service_keys: Iterable[bytes] ):
            
        with self._lock:
            
            return { 
                key for key in service_keys 
                
                if key not in self._blacklisted_file_domains and 
                   key not in self._blacklisted_tag_domains
            }
            

    def GetRules( self ):

        with self._lock:

            return dict( self._domain_rules )



    def GetChanges( self, old_domain_filter: "DomainFilter" ):
        
        old_rules = old_domain_filter.GetRules()

        new_rules = [ ( s_key, s_type ) for ( s_key, s_type ) in self._domain_rules if s_key not in old_rules ]
        changed_rules = [] # to keep this as close to TagFilter as possible
        deleted_rules = [ ( s_key, s_type ) for ( s_key, s_type ) in old_rules if s_key not in self._domain_rules ]
        
        return ( new_rules, changed_rules, deleted_rules )
        
    
    def GetChangesSummaryText( self, old_tag_filter: "DomainFilter" ):
        
        ( new_rules, changed_rules, deleted_rules ) = self.GetChanges( old_tag_filter )
        
        summary_components = []
        
        if len( new_rules ) > 0:
            
            summary_components.append( 'Added {} rules'.format( HydrusData.ToHumanInt( len( new_rules ) ) ) )
                
        
        if len( changed_rules ) > 0:
            
            summary_components.append( 'Changed {} rules'.format( HydrusData.ToHumanInt( len( new_rules ) ) ) )
            
        
        if len( deleted_rules ) > 0:
                
            summary_components.append( 'Deleted {} rules'.format( HydrusData.ToHumanInt( len( new_rules ) ) ) )
        
        return os.linesep.join( summary_components )
        

    def AddRule(self, service_key: bytes, service_type: int ):

        with self._lock:

            self._domain_rules[service_key] = service_type

            self._UpdateRuleCache()


    def RemoveRule(self, service_key: bytes ):

        if service_key not in self._domain_rules:
            return

        with self._lock:

            del self._domain_rules[service_key]

            self._UpdateRuleCache()


    def DomainOK(self, service_key: bytes ):

        with self._lock:

            return service_key not in self._blacklisted_file_domains and \
                   service_key not in self._blacklisted_tag_domains

         
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_DOMAIN_FILTER] = DomainFilter
